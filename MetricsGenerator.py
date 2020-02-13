import logging
import lxml
import argparse
import pyexcelerate
import jinja2
from template import jinja_string

def arg_parse(parser):
    parser.add_argument('-in_memorymap', '--in_memorymap', nargs='*', help="DATAFLASH, ROM, RAM memories content repartition", required=False, default="")
    parser.add_argument('-in_ldscript', '--in_ldscript', nargs='*', help="linker information for ROM and RAM memories regions", required=False, default="")
    parser.add_argument('-in_fee', '--in_fee', nargs='*', help="DATAFLASH memory data usage", required=False, default="")
    parser.add_argument('-in_ea', '--in_ea', nargs='*', help="EEPROM memory data usage", required=False, default="")
    parser.add_argument('-in_eep', '--in_eep', nargs='*', help="EEPROM memory configured size", required=False, default="")
    parser.add_argument('-in_memconfig', '--in_memconfig', nargs='*', help="EEPROM memory configuration", required=False, default="")
    parser.add_argument('-in_mapfile', '--in_mapfile', nargs='*', help="ROM and RAM memories data usage", required=False, default="")
    parser.add_argument('-in_dep', '--in_dep', nargs='*', help="dependencies directory of all the compiled source files", required=False, default="")
    parser.add_argument('-in_cont_mod', '--in_cont_mod', nargs='*', help="information regarding the contributors and the modules", required=False, default="")
    parser.add_argument('-out_HTML_format', '--out_html', help="output path for HTML format type results", required=False, default="")
    parser.add_argument('-out_xlsx_format', '--out_xlsx', help="output path for EXCEL format type results", required=False, default="")
    parser.add_argument('-out_log', '--out_log', help="output path for log file", required=False, default="")


def set_logger(path):
    # logger creation and setting
    logger = logging.getLogger('result')
    hdlr = logging.FileHandler(path + '/MetricsGenerator.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)
    open(path + '/MetricsGenerator.log', 'w').close()
    return logger


def main():
    template = jinja2.Template(jinja_string)
    users = ["John", "Sam", "Jooe"]
    output = template.render(title="Users", users=users)
    with open("test.html", "w") as handler:
        handler.write(output)


if __name__ == "__main__":
    main()
# regex for ldscript
# \w+\s+: org = 0[xX][0-9a-fA-f]+, len = [0-9(*]+(k)*( - [()0-9*]+)*

