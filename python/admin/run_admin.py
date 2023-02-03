#! /usr/bin/python3
""" provide a rest/api to a MySQL Database using Flask """

import json
from datetime import datetime
import flask

from librar.log import log, debug, init as log_init
from librar.policy import this_policy as policy
from librar import mysql as sql
from librar import registry
from librar import pdns
from librar import accounts
from librar import domobj
from librar import validate
from librar import common_ui
from librar import static_data
from admin import load_schema

# pylint: disable=unused-wildcard-import, wildcard-import
from backend import dom_handler
from backend.dom_plugins import *

ASKS = ["=", "!=", "<>", "<", ">", ">=", "<=", "like", "regexp"]

schema = {}


def response(code, data):
    """ return object {reason} with code {val} """
    resp = flask.make_response(flask.jsonify(data), code)
    resp.charset = 'utf-8'
    return resp


def json_abort(message):
    return response(499, {"error": message})


def find_best_index(idxes):
    """ Find shortest / best index from list of {idxes} """
    if ":primary:" in idxes:
        return ":primary:"
    most_col = 100
    ret_idx = None
    for idx in idxes:
        ncols = len(idxes[idx]["columns"])
        if "unique" in idxes[idx] and idxes[idx]["unique"] and ncols < most_col:
            most_col = ncols
            ret_idx = idx
    return ret_idx


def add_data(data, this_col):
    """ convert {data} to SQL string """
    if this_col["is_plain_int"]:
        return str(int(data))
    if this_col["type"] == "boolean":
        return "1" if data else "0"
    if not isinstance(data, str):
        data = str(data)
    return "unhex('" + "".join([hex(ord(a))[2:] for a in data]) + "')"


def clean_list_string(data):
    """ convert string or comma separated list to list """
    if isinstance(data, list):
        return data
    if isinstance(data, str) and data.find(","):
        return [r.strip() for r in data.split(",")]
    return [data]


def prepare_row_data(rows, table):
    """ format {rows} from {table} for JSON output """
    for row in rows:
        for col in list(row):
            if row[col] is None:
                del row[col]
            else:
                row[col] = clean_col_data(row[col], table, col)
                if ("enums" in schema[":more:"] and col in schema[":more:"]["enums"]
                        and row[col] in schema[":more:"]["enums"][col]):
                    row[col] = {":value:": row[col], ":text:": schema[":more:"]["enums"][col][row[col]]}


def clean_col_data(data, table, column):
    """ JSON format {data} from {table}.{column} """
    if data is None or column[0] == ":":
        return data

    ret = data
    this_col = schema[table]["columns"][column]

    if this_col["type"] == "boolean":
        ret = int(data) != 0
    elif this_col["type"] == "decimal":
        ret = float(data)
    elif this_col["is_plain_int"]:
        ret = int(data)
    elif isinstance(data, datetime):
        ret = data.strftime('%Y-%m-%d %H:%M:%S')
    elif not isinstance(data, str):
        ret = str(data)

    return ret


def find_join_column(src_table, dst_table):
    """ return column in {src_table} used to join to {dst_table} """
    for col in schema[src_table]["columns"]:
        this_col = schema[src_table]["columns"][col]
        if "join" in this_col and this_col["join"]["table"] == dst_table:
            return col
    return None


def find_foreign_column(sql_joins, src_table, dstcol):
    """ add the {sql_joins} needed to join to destination {dstcol} """
    dst = dstcol.split(".")
    fmt = "join {dsttbl} {alias} on({srctbl}.{srccol}={alias}.{dstcol})"

    if len(dst) != 2:
        json_abort(f"Invalid column name `{dstcol}`")

    if dst[0] in schema[src_table]["columns"] and "join" in schema[src_table]["columns"][dst[0]]:
        src_col = schema[src_table]["columns"][dst[0]]
        alias = "__zz__" + dst[0]
        dstcol = alias + "." + dst[1]
        if alias in sql_joins:
            return dstcol, src_col["join"]["table"]

        sql_joins[alias] = fmt.format(dsttbl=src_col["join"]["table"],
                                      dstcol=src_col["join"]["column"],
                                      alias=alias,
                                      srctbl=src_table,
                                      srccol=dst[0])
        return dstcol, src_col["join"]["table"]

    col_name = find_join_column(src_table, dst[0])
    if col_name is None:
        json_abort(f"Could not find a join for `{dstcol}` to `{src_table}`")

    alias = "__zz__" + col_name
    dstcol = alias + "." + dst[1]

    if alias in sql_joins:
        return dstcol, dst[0]

    this_col = schema[src_table]["columns"][col_name]
    sql_joins[alias] = fmt.format(alias=alias,
                                  srctbl=src_table,
                                  srccol=col_name,
                                  dsttbl=dst[0],
                                  dstcol=this_col["join"]["column"])

    return dstcol, dst[0]


def each_where_obj(sql_joins, table, ask_item, where_obj):
    """ return `where` clauses for {where_obj} & comparison {ask_item} """
    where = []
    for where_itm in where_obj:
        tbl = table
        col = where_itm
        if where_itm.find(".") >= 0:
            col, tbl = find_foreign_column(sql_joins, table, col)
        elif col not in schema[table]["columns"]:
            json_abort(f"Column `{col}` is not in table `{table}`")

        if ask_item == "=" and isinstance(where_obj[where_itm], list):
            if (tbl not in schema) or (col not in schema[tbl]["columns"]):
                json_abort(f"Column `{col}` is not in table `{table}`")
            this_col = schema[tbl]["columns"][col]
            where.append("(" + where_itm + " in (" + ",".join([add_data(d, this_col)
                                                               for d in where_obj[where_itm]]) + ") )")
        else:
            clause = []
            for itm in clean_list_string(where_obj[where_itm]):
                only_col = col if col.find(".") < 0 else col.split(".")[1]
                clause.append(col + ask_item + add_data(itm, schema[tbl]["columns"][only_col]))

            where.append("(" + " or ".join(clause) + ")")

    return " and ".join(where) if len(where) > 0 else ""


def where_clause(table, sent):
    """ convert the {where_data} JSON into SQL """
    if "where" not in sent:
        return ""

    sql_joins = {}

    if isinstance(sent["where"], str):
        return sent["where"]

    if isinstance(sent["where"], object):
        for ask_item in sent["where"]:
            if ask_item not in ASKS:
                json_abort(f"Comparison `{ask_item}` not supported")
            where = each_where_obj(sql_joins, table, ask_item, sent["where"][ask_item])

    return " ".join([data for __, data in sql_joins.items()]) + (" where " + where) if len(where) > 0 else ""


def plain_value(data):
    """ extract data item from {data} """
    if not isinstance(data, dict):
        return str(data)
    if ":value:" in data:
        return data[":value:"]
    if "join" in data:
        return data[data["join"].split(".")[1]]
    return str(data)


def include_for_join(data):
    """ shall we retrieve this foreign record """
    if data is None:
        return False
    if isinstance(data, str) and data == "":
        return False
    return True


def mysql_abort(exc, state):
    """ abort on MySQL exception {exc} at {state} """
    json_abort({"mysql": {"code": exc.args[0], "message": exc.args[1], "state": state}})


def load_all_joins(need):
    """ Load all db data for joins {need}ed """
    join_data = {}
    for item in need:
        src = item.split(".")
        query = "select * from " + src[0] + " where " + item + " in ("

        this_col = schema[src[0]]["columns"][src[1]]

        clauses = [add_data(d, this_col) for d in need[item]]

        if len(clauses) <= 0:
            continue

        query = query + ",".join(clauses) + ")"
        ok, reply = sql.run_select(query)
        if not ok:
            return None

        prepare_row_data(reply, src[0])

        join_data[item] = {clean_col_data(cols[src[1]], src[0], src[1]): cols for cols in reply if src[1] in cols}

    return join_data


def join_this_column(table, col, which):
    """ do we want join data for this {table.col} """

    if which is None or len(which) == 0 or col[0] == ":":
        return None

    this_col = schema[table]["columns"][col]
    if "join" not in this_col:
        return None

    if ":all:" in which or col in which:
        return this_col["join"]["table"] + "." + this_col["join"]["column"]

    return None


def handle_joins(rows, which, basic_format):
    """ retrive foreign rows & merge into return {rows} """
    if ":more:" not in schema or "joins" not in schema[":more:"]:
        return

    need = {}
    for table in rows:
        for row in rows[table]:
            if isinstance(rows[table], list):
                cols = row
            else:
                cols = rows[table][row]

            for col in cols:
                if not include_for_join(cols[col]):
                    continue
                target = join_this_column(table, col, which)
                if target is None:
                    continue

                if target not in need:
                    need[target] = []

                if cols[col] not in need[target]:
                    need[target].append(cols[col])

    if len(need) <= 0:
        return

    join_data = load_all_joins(need)
    if basic_format:
        rows.update(join_data)
    else:
        add_join_data(rows, join_data, which)


def add_join_data(rows, join_data, which):
    """ replace a columns data with retrived foreign record """
    for table in rows:
        for row in list(rows[table]):
            if isinstance(rows[table], list):
                cols = row
            else:
                cols = rows[table][row]

            for col in list(cols):
                target = join_this_column(table, col, which)
                if target is not None and target in join_data:
                    if cols[col] in join_data[target]:
                        cols[col] = join_data[target][cols[col]]
                        cols[col][":join:"] = target


def make_insert_from_list(set_list, table):
    """ make multiline sql insert to {table} from {set_list} """
    cols = schema[table]["columns"]
    have_cols = []
    for this_set in set_list:
        if not isinstance(this_set, dict):
            json_abort("All items in a `set` modifier list must be objects")
        for col in this_set:
            if col not in cols:
                json_abort(f"Column {col} is not in table {table}")

            if col not in have_cols:
                have_cols.append(col)

    sep = " "
    query = f"insert into {table}(" + ",".join(have_cols) + ") values"
    for this_set in set_list:
        vals = []
        for col in have_cols:
            if col in this_set:
                vals.append(add_data(this_set[col], cols[col]))
            else:
                vals.append("NULL")
        query = query + sep + "(" + ",".join(vals) + ")"
        sep = ","

    return query


def unique_id(best_idx, row):
    """ format the index item for {row} """
    return "|".join([plain_value(row[idx]) for idx in best_idx])


def check_supplied_modifiers(sent, allowed):
    """ check the {sent} modifiers are in the {allowed} list """
    for modifier in sent:
        if modifier not in allowed:
            json_abort(f"The modifier '{modifier}' is not supported in this request")


def run_backend_start_ups():
    all_regs = registry.tld_lib.regs_file.data()
    have_types = {reg_data["type"]: True for __, reg_data in all_regs.items() if "type" in reg_data}
    for this_type, funcs in dom_handler.backend_plugins.items():
        if this_type in have_types and "start_up" in funcs:
            funcs["start_up"]()


application = flask.Flask("MySQL-Rest/API")
log_init(policy.policy("facility_python_code"), with_logging=policy.policy("log_python_code"))
sql.connect("admin")
schema = load_schema.load_db_schema()
registry.start_up()
pdns.start_up()
run_backend_start_ups()

site_currency = policy.policy("currency")
if not validate.valid_currency(site_currency):
    raise ValueError("ERROR: Main policy.currency is not set up correctly")


@application.before_request
def before_request():
    if registry.tld_lib.check_for_new_files():
        run_backend_start_ups()


@application.route("/adm/v1", methods=['GET'])
def hello():
    """ respond with a `hello` to confirm working """
    return f"MySql-Auto-Rest/API: {sql.my_database}\n\n"


@application.route("/adm/v1/meta/schema", methods=['GET'])
def give_schema():
    """ respond with full schema """
    global schema
    schema = load_schema.load_db_schema()
    return response(200, schema)


@application.route("/adm/v1/meta/schema/<table>", methods=['GET'])
def give_table_schema(table):
    """ respond with schema for one <table> """
    if table not in schema:
        json_abort(f"Table '{table}' does not exist")
    return response(200, schema[table])


def make_order_clause(sent, table):
    """ build the `order by` clause, where present """
    this_cols = schema[table]["columns"]
    order_list = clean_list_string(sent["order"])

    for order in order_list:
        tst_order = order
        if order.find(" ") >= 0:
            tst = order.split(" ")
            tst_order = tst[0]
            if tst[1] not in ("asc", "desc"):
                json_abort(f"Only 'asc'/'desc' are allowed as 'order' modifiers, not '{tst[1]}'")

        if tst_order not in this_cols:
            json_abort(f"Column '{order}' not in table '{table}'")

    return " order by " + ",".join(order_list)


def build_sql(table, sent, start_sql):
    """ build the SQL needed to run the users query on {table} """
    query = (start_sql + where_clause(table, sent) + (make_order_clause(sent, table) if "order" in sent else ""))

    start = 0
    if "limit" in sent:
        query = query + " limit " + str(int(sent["limit"]))
        if "skip" in sent:
            start = int(sent["skip"])
            query = query + " offset " + str(start)
    else:
        if "skip" in sent:
            json_abort("`skip` without `limit` is not allowed")

    return start, query


def get_sql_rows(query, start):
    """ run the {query} and return the rows """
    ok, reply = sql.run_select(query)
    if not ok or len(reply) <= 0:
        return {}, 200

    rowid = start + 1
    for row in reply:
        row[":rowid:"] = rowid
        rowid = rowid + 1

    return reply


def process_one_set(set_clause, table):
    """ turn {set_clause} object into a sql insert statement """
    ret = []
    cols = schema[table]["columns"]
    for col in set_clause:
        if col not in cols:
            json_abort("Column {col} not in table {table}")

        ret.append(col + "=" + add_data(set_clause[col], cols[col]))
    return ret


def get_idx_cols(table, sent):
    """ get suitable list of index columns for {table} """
    idx_cols = None
    this_idxs = schema[table]["indexes"]
    if "by" in sent:
        snt_by = sent["by"]
        if isinstance(snt_by, str) and snt_by in this_idxs:
            if "unique" in this_idxs[snt_by] and this_idxs[snt_by]["unique"]:
                idx_cols = this_idxs[snt_by]["columns"]
        else:
            idx_cols = clean_list_string(snt_by)
            for idx in idx_cols:
                if not (idx == ":rowid:" or idx in schema[table]["columns"]):
                    json_abort("Bad column name in `by` clause")
    if idx_cols is None and len(this_idxs) > 0:
        idx_cols = this_idxs[find_best_index(this_idxs)]["columns"]

    if idx_cols is None:
        idx_cols = [":rowid:"]

    return idx_cols


@application.route("/adm/v1/data/<table>", methods=['PUT'])
def insert_table_row(table):
    """ do an sql insert on {table} """
    if table not in schema:
        json_abort(f"Table '{table}' does not exist")

    if (flask.request.json is None) or ("set" not in flask.request.json):
        json_abort("A `set` clause is mandatory for an INSERT")

    sent = flask.request.json
    check_supplied_modifiers(sent, ["set"])

    if not isinstance(sent["set"], (dict, list)):
        json_abort("In an INSERT, the `set` clause must be an object or list type")

    if isinstance(sent["set"], dict):
        set_list = process_one_set(sent["set"], table)
        query = f"insert into {table} set " + ",".join(set_list)
    else:
        query = make_insert_from_list(sent["set"], table)

    num_rows, row_id = sql.sql_exec(query)

    ret = {"affected_rows": num_rows}
    if ret["affected_rows"] == 1:
        if row_id > 0:
            ret["row_id"] = row_id

    return response(200, ret)


@application.route("/adm/v1/data/<table>", methods=['PATCH'])
def update_table_row(table):
    """ do an sql update on {table} """
    if table not in schema:
        return json_abort(f"Table '{table}' does not exist")

    if (flask.request.json is None) or ("set" not in flask.request.json):
        return json_abort("A `set` clause is mandatory for an UPDATE")

    sent = flask.request.json
    check_supplied_modifiers(sent, ["where", "limit", "set"])

    if not isinstance(sent["set"], dict):
        return json_abort("In an UPDATE, the `set` clause must be an object type")

    set_list = process_one_set(sent["set"], table)
    query = f"update {table} set " + ",".join(set_list)
    query = build_sql(table, sent, query)[1]

    num_rows, __ = sql.sql_exec(query)
    if num_rows is not None:
        return response(200, {"affected_rows": num_rows})
    return response(499, None)


@application.route("/adm/v1/data/<table>", methods=['DELETE'])
def delete_table_row(table):
    """ do an sql delete on {table} """
    if table not in schema:
        json_abort(f"Table '{table}' does not exist")

    if (flask.request.json is None) or ("where" not in flask.request.json):
        json_abort("The `where` clause is mandatory for a DELETE")

    check_supplied_modifiers(flask.request.json, ["where", "limit"])

    query = build_sql(table, flask.request.json, f"delete from {table} ")[1]

    num_rows, __ = sql.sql_exec(query)
    if num_rows is not None:
        return response(200, {"affected_rows": num_rows})
    return response(499, None)


@application.route("/adm/v1/user/transaction", methods=['POST'])
def post_user_transaction():
    if flask.request.json is None or not sql.has_data(flask.request.json, ["user_id", "amount", "description"]):
        return response(499, "Missing or invalid data")

    json = flask.request.json
    user_id = json["user_id"]

    if not isinstance(user_id, int):
        return response(499, "Missing or invalid data")
    if (amount := validate.valid_float(json["amount"])) is None:
        return response(499, "Invalid amount")
    if not validate.is_valid_display_name(json["description"]):
        return response(499, "Invalid description")

    ok, user_db = sql.sql_select("users", {"user_id": user_id})
    if not ok or not user_db or len(user_db) <= 0:
        return response(499, "Invalid user_id given")

    amount *= static_data.POW10[site_currency["decimal"]]
    amount = int(round(amount, 0))

    ok, trans_id = accounts.apply_transaction(user_id, amount, "Admin: " + json["description"], as_admin=True)
    if not ok:
        return response(499, trans_id)

    return response(200, True)


@application.route("/adm/v1/regs/<domain>", methods=['GET'])
def get_registry_data(domain):
    """ get registry data """
    if not validate.is_valid_fqdn(domain):
        return response(499, "Invalid domain name")
    dom = domobj.Domain()
    ok, reply = dom.load_name(domain)
    if not ok:
        return response(499, reply)

    action = "dom/rawinfo"
    bke_job = {
        "job_id": 99,
        "backend_id": "TEST",
        "authcode": "some-auth-code",
        "job_type": action,
        "num_years": 1,
        "domain_id": dom.dom_db["domain_id"]
    }
    this_handler = dom_handler.backend_plugins[dom.registry["type"]]
    if action not in this_handler:
        return response(499, f"Unsupport action '{action}' for type='{dom.registry['type']}'")

    if (reply := this_handler[action](bke_job, dom.dom_db)) is None:
        return response(499, "Error getting domain info from backend")
    return response(200, reply)


@application.route("/adm/v1/dns/<domain>", methods=['GET'])
def get_dns_data(domain):
    """ get pdns data """
    if not validate.is_valid_fqdn(domain):
        return response(499, "Invalid domain name")
    if not pdns.zone_exists(domain):
        return response(499, "No data")

    if (dns := pdns.load_zone(domain)) is None:
        return response(499, "No data")

    if dns and "dnssec" in dns and dns["dnssec"]:
        dns["keys"] = pdns.load_zone_keys(domain)
        dns["ds"] = pdns.find_best_ds(dns["keys"])

    return response(200, {"name": domain, "dns": dns})


@application.route("/adm/v1/data/<table>", methods=['GET', 'POST'])
def get_table_row(table):
    """ run select queries """
    if table not in schema:
        json_abort(f"Table '{table}' does not exist")

    sent = None
    if flask.request.json is not None:
        sent = flask.request.json
    if sent is None and flask.request.method == "POST":
        sent = flask.request.form
    if sent is None and flask.request.method == "GET":
        sent = flask.request.args

    check_supplied_modifiers(sent, ["where", "limit", "skip", "by", "order", "join", "join-basic"])

    start, query = build_sql(table, sent, f"select {table}.* from {table} ")
    sql_rows = get_sql_rows(query, start)

    if not isinstance(sql_rows, list):
        return response(200, sql_rows)

    prepare_row_data(sql_rows, table)

    if "by" in sent:
        ret_rows = {table: {unique_id(get_idx_cols(table, sent), tmp): tmp for tmp in sql_rows}}
    else:
        ret_rows = {table: sql_rows}

    if "join" in sent:
        join = sent["join"]
        if isinstance(join, bool):
            join = [":all:"] if join else None
        if join is not None:
            handle_joins(ret_rows, clean_list_string(join), ("join-basic" in sent and sent["join-basic"]))

    return response(200, ret_rows)


@application.route('/adm/v1/config', methods=['GET'])
def get_config():
    config = common_ui.ui_config()
    config["schema"] = load_schema.load_db_schema()
    return response(200, config)


if __name__ == "__main__":
    log_init(with_debug=True)
    application.run()
    sql.cnx.close()
