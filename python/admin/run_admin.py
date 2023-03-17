#! /usr/bin/python3
# (c) Copyright 2019-2023, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" Admin webui """

from datetime import datetime
import subprocess
import flask

from librar.log import log, init as log_init
from librar.policy import this_policy as policy
from librar.mysql import sql_server as sql
from librar import registry, pdns, accounts, domobj, passwd, validate, common_ui

from backend import backend_creator, libback

ASKS = ["=", "!=", "<>", "<", ">", ">=", "<=", "like", "regexp"]
CHECK_HAS_COLUMN = ["amended_dt", "created_dt"]
DOMAIN_JOB_TYPES = {"PUT": "dom/create", "PATCH": "dom/update", "DELETE": "dom/delete"}

HAS_COLUMN = {}


def find_serial_column(table):
    if table not in sql.schema or "columns" not in sql.schema[table]:
        return None
    for col, col_data in sql.schema[table]["columns"].items():
        if "serial" in col_data and col_data["serial"]:
            return col
    return None


def set_amended_and_created():
    global HAS_COLUMN
    HAS_COLUMN = {col: {} for col in CHECK_HAS_COLUMN}
    for table, tbl_data in sql.schema.items():
        if "columns" not in tbl_data:
            continue

        for col in CHECK_HAS_COLUMN:
            if col in tbl_data["columns"]:
                HAS_COLUMN[col][table] = True


def post_table_trigger(table, action, row_id=None, where=None):
    if row_id is None and where is None:
        log(f"ERROR: post_table_trigger on '{table}' with '{action}' wasn't given any keys")
        return

    if table == "sysadmins":
        subprocess.run(["/usr/local/bin/make_admin_logins"],
                       stderr=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL,
                       check=False)
        return

    this_where = None
    if where is not None:
        this_where = where[7:]
    elif row_id is not None:
        if (col := find_serial_column(table)) is None:
            return
        this_where = {col: row_id}

    if table == "domains" and this_where is not None:
        post_trigger_domains(action, this_where)


def post_trigger_domains(action, this_where):
    if action not in DOMAIN_JOB_TYPES:
        log(f"ERROR: Action '{action}' not in DOMAIN_JOB_TYPES")
        return

    ok, dom_db = sql.sql_select_one("domains", this_where)
    if ok and dom_db and len(dom_db):
        backend_creator.make_job(DOMAIN_JOB_TYPES[action], dom_db)


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
    if data is None:
        return "NULL"
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
                if ("enums" in sql.schema[":more:"] and col in sql.schema[":more:"]["enums"]
                        and row[col] in sql.schema[":more:"]["enums"][col]):
                    row[col] = {":value:": row[col], ":text:": sql.schema[":more:"]["enums"][col][row[col]]}


def clean_col_data(data, table, column):
    """ JSON format {data} from {table}.{column} """
    if data is None or column[0] == ":":
        return data

    ret = data
    this_col = sql.schema[table]["columns"][column]

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
    for col in sql.schema[src_table]["columns"]:
        this_col = sql.schema[src_table]["columns"][col]
        if "join" in this_col and this_col["join"]["table"] == dst_table:
            return col
    return None


def find_foreign_column(sql_joins, src_table, dstcol):
    """ add the {sql_joins} needed to join to destination {dstcol} """
    dst = dstcol.split(".")
    fmt = "join {dsttbl} {alias} on({srctbl}.{srccol}={alias}.{dstcol})"

    if len(dst) != 2:
        return json_abort(f"Invalid column name `{dstcol}`")

    if dst[0] in sql.schema[src_table]["columns"] and "join" in sql.schema[src_table]["columns"][dst[0]]:
        src_col = sql.schema[src_table]["columns"][dst[0]]
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
        return json_abort(f"Could not find a join for `{dstcol}` to `{src_table}`")

    alias = "__zz__" + col_name
    dstcol = alias + "." + dst[1]

    if alias in sql_joins:
        return dstcol, dst[0]

    this_col = sql.schema[src_table]["columns"][col_name]
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
        elif col not in sql.schema[tbl]["columns"]:
            return json_abort(f"Column `{col}` is not in table `{table}`")

        if ask_item == "=" and isinstance(where_obj[where_itm], list):
            if (tbl not in sql.schema) or (col not in sql.schema[tbl]["columns"]):
                return json_abort(f"Column `{col}` is not in table `{table}`")
            this_col = sql.schema[tbl]["columns"][col]
            where.append("(" + where_itm + " in (" + ",".join([add_data(d, this_col)
                                                               for d in where_obj[where_itm]]) + ") )")
        else:
            clause = []
            for itm in clean_list_string(where_obj[where_itm]):
                only_col = col if col.find(".") < 0 else col.split(".")[1]
                clause.append(col + " " + ask_item + " " + add_data(itm, sql.schema[tbl]["columns"][only_col]))

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
                return json_abort(f"Comparison `{ask_item}` not supported")
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
    return json_abort({"mysql": {"code": exc.args[0], "message": exc.args[1], "state": state}})


def load_all_joins(need):
    """ Load all db data for joins {need}ed """
    join_data = {}
    for item in need:
        src = item.split(".")
        query = "select * from " + src[0] + " where " + item + " in ("

        this_col = sql.schema[src[0]]["columns"][src[1]]

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

    this_col = sql.schema[table]["columns"][col]
    if "join" not in this_col:
        return None

    if ":all:" in which or col in which:
        return this_col["join"]["table"] + "." + this_col["join"]["column"]

    return None


def handle_joins(rows, which, basic_format):
    """ retrive foreign rows & merge into return {rows} """
    if ":more:" not in sql.schema or "joins" not in sql.schema[":more:"]:
        return

    need = {}
    for table in rows:
        for row in rows[table]:
            cols = row if isinstance(rows[table], list) else rows[table][row]
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
            cols = row if isinstance(rows[table], list) else rows[table][row]
            for col in list(cols):
                if ((target := join_this_column(table, col, which)) is not None and target in join_data
                        and cols[col] in join_data[target]):
                    cols[col] = join_data[target][cols[col]]
                    cols[col][":join:"] = target


def unique_id(best_idx, row):
    """ format the index item for {row} """
    return "|".join([plain_value(row[idx]) for idx in best_idx])


def check_supplied_modifiers(sent, allowed):
    """ check the {sent} modifiers are in the {allowed} list """
    for modifier in sent:
        if modifier not in allowed:
            json_abort(f"The modifier '{modifier}' is not supported in this request")


application = flask.Flask("MySQL-Rest/API")
log_init("logging_admin")
sql.connect("admin")
sql.make_schema()
set_amended_and_created()
registry.start_up()
pdns.start_up()
libback.start_ups()

site_currency = policy.policy("currency")
if not validate.valid_currency(site_currency):
    raise ValueError("ERROR: Main policy.currency is not set up correctly")


@application.before_request
def before_request():
    if registry.tld_lib.check_for_new_files():
        libback.start_ups()


@application.route("/adm/v1", methods=['GET'])
def hello():
    """ respond with a `hello` to confirm working """
    return f"MySql-Auto-Rest/API: {sql.credentials['database']}\n\n"


@application.route("/adm/v1/meta/schema/<table>", methods=['GET'])
def send_table_schema(table):
    """ respond with sql.schema for one <table> """
    if table not in sql.schema:
        return json_abort(f"Table '{table}' does not exist")
    return response(200, sql.schema[table])


def make_order_clause(sent, table):
    """ build the `order by` clause, where present """
    this_cols = sql.schema[table]["columns"]
    order_list = clean_list_string(sent["order"])

    for order in order_list:
        tst_order = order
        if order.find(" ") >= 0:
            tst = order.split(" ")
            tst_order = tst[0]
            if tst[1] not in ("asc", "desc"):
                return json_abort(f"Only 'asc'/'desc' are allowed as 'order' modifiers, not '{tst[1]}'")

        if tst_order not in this_cols:
            return json_abort(f"Column '{order}' not in table '{table}'")

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
            return json_abort("`skip` without `limit` is not allowed")

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
    cols = sql.schema[table]["columns"]
    for col in set_clause:
        if col not in cols:
            return False, f"Column {col} not in table {table}"
        val = add_data(set_clause[col], cols[col])
        if col in CHECK_HAS_COLUMN:
            val = "now()"
        elif col in ["htpasswd", "password"]:
            val = '"' + passwd.crypt(set_clause[col]) + '"'
        ret.append(col + "=" + val)
    return True, ret


def get_idx_cols(table, sent):
    """ get suitable list of index columns for {table} """
    idx_cols = None
    this_idxs = sql.schema[table]["indexes"]
    if "by" in sent:
        snt_by = sent["by"]
        if isinstance(snt_by, str) and snt_by in this_idxs:
            if "unique" in this_idxs[snt_by] and this_idxs[snt_by]["unique"]:
                idx_cols = this_idxs[snt_by]["columns"]
        else:
            idx_cols = clean_list_string(snt_by)
            for idx in idx_cols:
                if not (idx == ":rowid:" or idx in sql.schema[table]["columns"]):
                    return json_abort("Bad column name in `by` clause")
    if idx_cols is None and len(this_idxs) > 0:
        idx_cols = this_idxs[find_best_index(this_idxs)]["columns"]

    if idx_cols is None:
        idx_cols = [":rowid:"]

    return idx_cols


@application.route("/adm/v1/data/<table>", methods=['PUT'])
def insert_table_row(table):
    """ do an sql insert on {table} """
    if table not in sql.schema:
        return json_abort(f"Table '{table}' does not exist")

    if (flask.request.json is None) or ("set" not in flask.request.json):
        return json_abort("A `set` clause is mandatory for an INSERT")

    sent = flask.request.json
    check_supplied_modifiers(sent, ["set"])

    if "set" not in sent or not isinstance(sent["set"], dict):
        return json_abort("In an INSERT, the `set` clause must be an object or list type")

    for col in CHECK_HAS_COLUMN:
        if table in HAS_COLUMN[col] and col not in sent["set"]:
            sent["set"][col] = None

    ok, set_list = process_one_set(sent["set"], table)
    if not ok:
        return json_abort(set_list)
    query = f"insert into {table} set " + ",".join(set_list)

    num_rows, row_id = sql.sql_exec(query)
    if num_rows is False:
        return json_abort(row_id)

    ret = {"affected_rows": num_rows}
    if num_rows == 1 and row_id > 0:
        ret["row_id"] = row_id

    post_table_trigger(table, "PUT", row_id=row_id)
    return response(200, ret)


@application.route("/adm/v1/data/<table>", methods=['PATCH'])
def update_table_row(table):
    """ do an sql update on {table} """
    if table not in sql.schema:
        return json_abort(f"Table '{table}' does not exist")

    if (flask.request.json is None) or ("set" not in flask.request.json):
        return json_abort("A `set` clause is mandatory for an UPDATE")

    sent = flask.request.json
    check_supplied_modifiers(sent, ["where", "limit", "set"])

    if not isinstance(sent["set"], dict):
        return json_abort("In an UPDATE, the `set` clause must be an object type")

    if table in HAS_COLUMN["amended_dt"] and "amended_dt" not in sent["set"]:
        sent["set"]["amended_dt"] = None

    ok, set_list = process_one_set(sent["set"], table)
    if not ok:
        return json_abort(set_list)
    query = f"update {table} set " + ",".join(set_list)
    __, query = build_sql(table, sent, query)

    num_rows, __ = sql.sql_exec(query)
    if num_rows is not None:
        post_table_trigger(table, "PATCH", where=where_clause(table, sent))
        return response(200, {"affected_rows": num_rows})

    return response(499, None)


@application.route("/adm/v1/data/<table>", methods=['DELETE'])
def delete_table_row(table):
    """ do an sql delete on {table} """
    if table not in sql.schema:
        return json_abort(f"Table '{table}' does not exist")

    if (flask.request.json is None) or ("where" not in flask.request.json):
        return json_abort("The `where` clause is mandatory for a DELETE")

    check_supplied_modifiers(flask.request.json, ["where", "limit"])

    __, query = build_sql(table, flask.request.json, f"delete from {table} ")

    num_rows, __ = sql.sql_exec(query)
    if num_rows is not None:
        post_table_trigger(table, "DELETE", where=where_clause(table, flask.request.json))
        return response(200, {"affected_rows": num_rows})

    return response(499, None)


@application.route("/adm/v1/user/transaction", methods=['POST'])
def post_user_transaction():
    ok, reply = accounts.admin_trans(flask.request.json)
    if not ok:
        return json_abort(reply)
    return response(200, True)


@application.route("/adm/v1/regs/<domain>", methods=['GET'])
def get_registry_data(domain):
    """ get registry data """
    if not validate.is_valid_fqdn(domain):
        return json_abort("Invalid domain name")
    dom = domobj.Domain()
    ok, reply = dom.load_name(domain)
    if not ok:
        return json_abort(reply)

    action = "dom/rawinfo"
    bke_job = {
        "job_id": 99,
        "backend_id": "TEST",
        "authcode": "some-auth-code",
        "job_type": action,
        "num_years": 1,
        "domain_id": dom.dom_db["domain_id"]
    }
    if (reply := libback.run(action, dom.registry, bke_job, dom.dom_db)) is None:
        return json_abort("Error getting domain info from backend")
    return response(200, reply)


@application.route("/adm/v1/dns/<domain>", methods=['GET'])
def get_dns_data(domain):
    """ get pdns data """
    if not validate.is_valid_fqdn(domain) and not validate.is_valid_tld(domain):
        return json_abort("Invalid domain name")
    pdns.create_zone(domain, ensure_zone=True)
    if (dns := pdns.load_zone(domain)) is None:
        return json_abort("PowerDNS data failed to load")
    if dns and "dnssec" in dns and dns["dnssec"]:
        dns["keys"] = pdns.load_zone_keys(domain)
        dns["ds"] = pdns.find_best_ds(dns["keys"])

    return response(200, {"name": domain, "dns": dns})


@application.route("/adm/v1/data/<table>", methods=['GET', 'POST'])
def get_table_row(table):
    """ run select queries """
    if table not in sql.schema:
        return json_abort(f"Table '{table}' does not exist")

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
        my_joins = sent["join"]
        if isinstance(my_joins, bool):
            my_joins = [":all:"] if my_joins else None
        if my_joins is not None:
            handle_joins(ret_rows, clean_list_string(my_joins), ("join-basic" in sent and sent["join-basic"]))

    return response(200, ret_rows)


@application.route('/adm/v1/config', methods=['GET'])
def get_config():
    config = common_ui.ui_config()
    config["schema"] = sql.schema
    return response(200, config)


def main():
    log_init(with_debug=True)
    application.run()
    sql.close()


if __name__ == "__main__":
    main()
