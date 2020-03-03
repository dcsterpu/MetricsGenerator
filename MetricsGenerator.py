import logging
from lxml import etree, objectify
import argparse
import pyexcelerate
import jinja2
from template import jinja_string
import xlrd
from xml.dom import minidom
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
import xml.etree.ElementTree as ET
import re
#import pandas
from decimal import Decimal
from pyexcelerate import Workbook, Color, Style, Fill
import os


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


def prettify_xml(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")


def check_if_xml_is_wellformed(file):
    parser = make_parser()
    parser.setContentHandler(ContentHandler())
    parser.parse(file)


def main():
    parser = argparse.ArgumentParser()
    arg_parse(parser)
    args = parser.parse_args()
    outputxlsx = args.out_xlsx
    outputlog = args.out_log
    ea_path = args.in_ea
    eep_path = args.in_eep
    fee_path = args.in_fee
    ldscript_path = args.in_ldscript
    memorymap_path = args.in_memorymap
    mapfile_path = args.in_mapfile
    memconfig_path = args.in_memconfig
    dep_path = args.in_dep
    contMod_path = args.in_cont_mod
    #dir_path = os.path.dirname(os.path.realpath(__file__))
    logger = set_logger(outputlog)


    data_flash,total_dataflash = parse_Memory_Map(memorymap_path,logger)
    data_fee = parse_in_fee(fee_path,logger)
    data_ea = parse_in_ea(ea_path,logger)
    #modules = parse_cont_mod(contMod_path, logger)
    eep_total_size = parse_in_eep(eep_path,logger)
    eeprom_blocks,modules = parse_mem_config(memconfig_path,logger)
    memory_regions = parse_mapfile(mapfile_path,logger)
    regions = parse_ldscript(ldscript_path,logger)
    data_eeprom,eeprom_total_used_size = calculate_eeprom(data_ea,eep_total_size)
    DataflashUsed = calcultate_dataflash(data_fee)
    scopes,symbol_list,memory_regions,output_sections,ram_memory,rom_memory,variables_list,o_sections = calculate_ram_rom(mapfile_path,regions,logger)
    verify_map_ld(memory_regions, regions,logger)
    #in_dep(dep_path)
    profile_blocks,min_rom,max_rom,min_ram,max_ram = create_excel(scopes,symbol_list,memory_regions,output_sections,ram_memory,rom_memory,variables_list,o_sections,data_fee,DataflashUsed,eep_total_size, data_eeprom,eeprom_total_used_size,eeprom_blocks,modules,outputxlsx,data_flash,total_dataflash)

    ram_used_memory = 0
    rom_used_memory = 0
    for variable in variables_list:
        if variable['TYPE'] == 'RAM':
            ram_used_memory = ram_used_memory + variable['SIZE']
        if variable['TYPE'] == 'ROM':
            rom_used_memory = rom_used_memory + variable['SIZE']

    a = len(data_flash)
    template = jinja2.Template(jinja_string)
    users = ["John", "Sam", "Jooe"]
    output = template.render(title="Us", output_sections=output_sections, ram_used_memory = ram_used_memory, rom_used_memory = rom_used_memory, data_eeprom = data_eeprom, profile_blocks = profile_blocks, min_ram = min_ram, max_ram = max_ram, min_rom = min_rom, max_rom = max_rom, eep_total_size = eep_total_size, eeprom_total_used_size = eeprom_total_used_size,data_flash_start = data_flash[0]['START'], data_flash_end = data_flash[a-1]['END'], total_dataflash= total_dataflash, DataflashUsed= DataflashUsed)
    with open("test.html", "w") as handler:
        handler.write(output)


def parse_cont_mod(contMod_path, logger):
    modules = []
    try:
        for file in contMod_path:
            parser = etree.XMLParser(remove_comments=True)
            tree = objectify.parse(file, parser=parser)
            root = tree.getroot()
            module = root.findall(".//NAME")
            for data in module:
                if data.getparent().tag == "MODULE":
                    obj = {}
                    obj['NAME'] = data['NAME'].text
                    modules.append(obj)
            logger.info("The cont_mod file is well-parsed " + file)
    except:
        logger.error("ERROR parsing the cont_mod file " + file)

    for module in modules:
        print(module)

    return modules

def parse_Memory_Map(memorymap_path,logger):
    #010
    data_flash = []
    total_dataflash = 0
    try:
        for path in memorymap_path:
            workbook = xlrd.open_workbook(path)
            sheets_name = workbook.sheet_names()
            worksheet = workbook.sheet_by_name(sheets_name[2])

            rows = []
            for i, row in enumerate(range(worksheet.nrows)):
                r= []
                if i != 0 and i != 1:
                    for j, col in enumerate(range(worksheet.ncols)):
                        if j != 0:
                            r.append(worksheet.cell_value(i, j))
                    rows.append(r)

            df0 =0
            for row in rows:
                if row[0] != 'DF1':
                    df0 = df0 + 1
                if row[0] == 'DF1':
                    break
            it = 0
            for row in rows:
                if it < df0:
                    obj = {}
                    obj['SECTOR'] = row[1]
                    obj['START'] = row[2]
                    obj['END'] = row[3]
                    obj['DATA'] = row[4]
                    obj['SIZE'] = row[5]
                    data_flash.append(obj)
                if it > df0:
                    break
                it = it + 1

            logger.info("The MemoryMap file is well-parsed: " + path )
    except:
        logger.error("ERROR parsing the MemoryMap " + path)

        # for data in data_flash:
        #     size= 0
        #     if re.match('^[0-9]*[k,m,K,M][b,B]?', data['SIZE']):
        #         m = re.search('(.+)',data['SIZE'])
        #         if m:
        #             data['SIZE'] = int(m.group(0))
        #         m = re.search('(.+)[k,K][b,B]?', data['SIZE'])
        #         if m:
        #             data['SIZE'] = int(m.group(0))*1024
        #         m = re.search('(.+)[m,M][b,B]?', data['SIZE'])
        #         if m:
        #             data['SIZE'] = int(m.group(0)) * 1048576

    for data in data_flash:
        size = 0
        if re.match('^[0-9]*$',data['SIZE']):
            m = re.search('[0-9](.+)',data['SIZE'])
            if m:
                data['SIZE'] = (m.group(0))
        if re.match('^[0-9]*[kK]',data['SIZE']):
            m = re.search('[0-9]+',data['SIZE'])
            if m:
                data['SIZE'] = str(int(m.group(0)) * 1024)
        if re.match('^[0-9]*[mM]',data['SIZE']):
            m = re.search('[0-9](.+)',data['SIZE'])
            if m:
                data['SIZE'] = str(int(m.group(0)) *1048576)
        data['SIZE'] = int(data['SIZE'])


    for data in data_flash:
        total_dataflash = total_dataflash + data['SIZE']


    # for i in data_flash:
    #     print(i)
    return data_flash,total_dataflash


def parse_in_fee(fee_path,logger):
    data_flash_fee_final = []
    try:
        for file in fee_path:
            parser = etree.XMLParser(remove_comments=True)
            tree = objectify.parse(file, parser=parser)
            root = tree.getroot()
            data_flash_fee = root.findall(".//{http://www.tresos.de/_projects/DataModel2/06/data.xsd}ctr")
            for data in data_flash_fee:
                if data.getparent().tag == "{http://www.tresos.de/_projects/DataModel2/06/data.xsd}lst":
                    try:
                        if data.getparent().attrib['name'] == "FeeBlockConfiguration":
                            obj = {}
                            obj['NAME'] = data.attrib['name']
                            list_children = data.findall(".//{http://www.tresos.de/_projects/DataModel2/06/data.xsd}var")
                            for child in list_children:
                                try:
                                    if child.attrib['name'] == "FeeBlockNumber":
                                        obj['NUMBER-VALUE'] = child.attrib['value']
                                    if child.attrib['name'] == "FeeBlockSize":
                                        obj['SIZE-VALUE'] = int(child.attrib['value'])
                                except AttributeError:
                                    pass
                            data_flash_fee_final.append(obj)
                    except KeyError:
                        pass
            logger.info("The Fee file is well-parsed" + file)
    except:
        logger.error("ERROR parsing the Fee file " + file)

    # print("DATAFLASH FEE HERE.............................")
    # for data in data_flash_fee_final:
    #     print(data)
    # print("END OF FEE DATAFLASH............................")

    return data_flash_fee_final

def parse_in_ea(ea_path, logger):
    data_flash_ea_final =[]
    try:
        for file in ea_path:
            parser = etree.XMLParser(remove_comments=True)
            tree = objectify.parse(file, parser=parser)
            root = tree.getroot()
            data_flash_ea = root.findall(".//{http://www.tresos.de/_projects/DataModel2/06/data.xsd}ctr")
            for data in data_flash_ea:
                if data.getparent().tag == "{http://www.tresos.de/_projects/DataModel2/06/data.xsd}lst":
                    try:
                        if data.getparent().attrib['name'] == "EaBlockConfiguration":
                            obj = {}
                            obj['NAME'] = data.attrib['name']
                            list_children = data.findall(".//{http://www.tresos.de/_projects/DataModel2/06/data.xsd}var")
                            for child in list_children:
                                try:
                                    if child.attrib['name'] == "EaBlockNumber":
                                        obj['NUMBER-VALUE'] = child.attrib['value']
                                    if child.attrib['name'] == "EaBlockSize":
                                        obj['SIZE-VALUE'] = int(child.attrib['value'])
                                except:
                                    pass
                            data_flash_ea_final.append(obj)
                    except:
                        pass
            logger.info("The Ea file is well-parsed " + file )
    except:
        logger.error("ERROR parsing the Ea file " + file)
    # print("EEPROM EA HERE.............................")
    # for data in data_flash_ea_final:
    #     print(data)
    # print("END OF EA EEPROM............................")

    return data_flash_ea_final

def parse_in_eep(eep_path,logger):
    #069
    data_eep_final = []
    try:
        for file in eep_path:
            parser = etree.XMLParser(remove_comments=True)
            tree = objectify.parse(file, parser=parser)
            root = tree.getroot()
            data_eep = root.findall(".//{http://www.tresos.de/_projects/DataModel2/06/data.xsd}ctr")
            for data in data_eep:
                if data.getparent().tag == "{http://www.tresos.de/_projects/DataModel2/06/data.xsd}lst":
                    try:
                        if data.getparent().attrib['name'] == "EepInitConfiguration":
                            if data.attrib['name'] == "EepInitConfiguration":
                                obj = {}
                                obj['NAME'] = 'EepInitConfiguration'
                                list_children = data.findall(".//{http://www.tresos.de/_projects/DataModel2/06/data.xsd}var")
                                for child in list_children:
                                    try:
                                        if child.attrib['name'] == "EepSize":
                                            obj['VALUE'] = int(child.attrib['value'])
                                    except:
                                        pass
                                data_eep_final.append(obj)
                    except:
                        pass
            logger.info("The Eep file is well-parsed " + file)
    except:
        logger.error("ERROR parsing the Eep file " + file)
    # print("EEPROM EEP HERE.............................")
    # for data in data_eep_final:
    #     print(data)
    # print("END OF EEP EEPROM............................")
    eep_total_size = int(data_eep_final[0]['VALUE'])

    return eep_total_size


def parse_mem_config(memconfig_path, logger):
    eeprom_blocks = []
    modules = []
    try:
        for file in memconfig_path:
            parser = etree.XMLParser(remove_comments=True)
            tree = objectify.parse(file, parser=parser)
            root = tree.getroot()
            data_eeprom = root.findall(".//BLOCK")
            for data in data_eeprom:
                if data.getparent().tag == "BLOCKS":
                    obj = {}
                    obj['NAME'] = data.getchildren()[0].text
                    obj['REF'] = data.getchildren()[2].text
                    eeprom_blocks.append(obj)
            module = root.findall(".//PR-PORT-PROTOTYPE-REF")
            for data in module:
                if data.getparent().tag == "PR-PORT-PROTOTYPE-REFS" and data.getparent().getparent().tag == "BLOCK":
                    obj = {}
                    obj['NAME'] = data.text
                    obj['BLOCK'] = data.getparent().getparent()[0].text
                    obj['PROFILE'] = data.getparent().getparent()[2].text
                    modules.append(obj)
            logger.info("The MemConfig file is well-parsed " + file)
    except:
        logger.error("ERROR parsing the MemConfig file " + file)

    # print("MODULES.....................")
    # for module in modules:
    #     print(module)
    # print("END OF MODULES.................")


    # print("MEM CONFIG HERE................................")
    # for data in eeprom_blocks:
    #     print(data)
    # print("END OF MEM CONFIG................................")
    return eeprom_blocks, modules

def parse_mapfile(mapfile_path,logger):
    memory_regions = []
    try:
        for file in mapfile_path:
            parser = etree.XMLParser(remove_comments=True)
            tree = objectify.parse(file, parser=parser)
            root = tree.getroot()
            memory_region = root.findall(".//{http://www.hightec-rt.com/map/}MemoryRegion")
            for data in memory_region:
                if data.getparent().tag == "{http://www.hightec-rt.com/map/}MemoryConfiguration":
                    obj = {}
                    obj['NAME'] = data.attrib['name']
                    obj['ORIGIN'] = data.attrib['origin']
                    obj['LENGTH'] = data.attrib['length']
                    memory_regions.append(obj)
            logger.info("The MapFile file is well-parsed " + file)
    except:
        logger.error("ERROR parsing the MapFile file " + file)

    # print("MAPFILE HERE................................")
    # for data in memory_regions:
    #     print(data)
    # print("END OF MAPFILE................................")

    return memory_regions

def parse_ldscript(ldscript_path, logger):
    regions = []
    try:
        for path in ldscript_path:
            file = open(path)
            line = file.readline()
            while line:
                m = ''
                if re.search('\w+\s+: org = 0[xX][0-9a-fA-f]+, len = [0-9(*]+(k)*( - [()0-9*]+)*',line):
                    m = re.search('\w+\s+: org = 0[xX][0-9a-fA-f]+, len = [0-9(*]+(k)*( - [()0-9*]+)*',line).group(0)
                    obj = {}
                    obj['NAME'] = m.split()[0]
                    if re.search('^0{1}x{1}[0-9 a-z A-Z]{8},$',m.split()[4]):
                        obj['START-ADDRESS'] = m.split()[4][:-1]
                    if re.search('^[0-9]+[kKmM]?$',m.split()[7]):
                        obj['SIZE'] = m.split()[7]
                    else:
                        try:
                            string =  m.split()[7] + " " + m.split()[8] + " " + m.split()[9]
                            if re.search('^[(][0-9]+[kKmM] - [(][0-9]+[*][0-9]+[)][)]$',string):
                                obj['SIZE'] = string
                        except:
                            pass
                    regions.append(obj)
                line = file.readline()
            logger.info("The Ldscript file is well-parsed " + path)
    except:
        logger.error("ERROR parsing the Ldscript file " + path)
    # print('LD SCRIPT...............................')
    # for region in regions:
    #     print(region)
    # print('END OF LD SCRIPT...........................)')

    for data in regions:
        t1 = 0
        t2 = 0
        if re.match('^[0-9]*$',data['SIZE']):
            m = re.search('[0-9](.+)',data['SIZE'])
            if m:
                data['SIZE'] = (m.group(0))
        if re.match('^[0-9]*[kK]',data['SIZE']):
            m = re.search('[0-9]+',data['SIZE'])
            if m:
                data['SIZE'] = str(int(m.group(0)) * 1024)
        if re.match('^[0-9]*[mM]',data['SIZE']):
            m = re.search('[0-9](.+)',data['SIZE'])
            if m:
                data['SIZE'] = str(int(m.group(0)) *1048576)
        if re.match('^[(][0-9]+[kKmM] - [(][0-9]+[*][0-9]+[)][)]$',data['SIZE']):
            m = re.search('^[(][0-9]+[kKmM] - [(][0-9]+[*][0-9]+[)][)]$',data['SIZE'])
            if re.search('[kK]',m.group(0).split()[0]):
                t1 = int((re.search('[0-9]+',m.group(0).split()[0])).group(0)) * 1024
            if re.search('[mM]',m.group(0).split()[0]):
                t1 = int(re.search('[0-9]+',m.group(0).split()[0])) * 1048576
            n = re.search('[*][0-9]+',m.group(0).split()[2])
            t2 = int((re.search('[0-9]+',m.group(0).split()[2])).group(0)) * int((re.search('[0-9]+',n.group(0))).group(0))
            data['SIZE'] = str(t1 - t2)
        data['SIZE'] = int(data['SIZE'])
    # for region in regions:
    #     print(region)
    return regions

def EEPROM_Level1(EaBlockNumber, EaBlockSize):
    BlockDataOverhead = 2
    virtualPageSize = 64
    thisBlockPageNum = FindNecessaryContainerNum(contentSize=EaBlockSize + BlockDataOverhead, containerSize=virtualPageSize)
    thisCopyTotalSize = (thisBlockPageNum * virtualPageSize) + virtualPageSize
    return thisCopyTotalSize

def FindNecessaryContainerNum ( contentSize, containerSize):
    result = int(contentSize / containerSize)
    if (result * containerSize) < contentSize:
        result = result + 1
    return result

def calculate_eeprom(data_ea,eep_total_size):
    #lvl 1
    #074
    EEPROMUsedMemory = 0
    for data in data_ea:
        EEPROMUsedMemory = EEPROMUsedMemory + int(data['NUMBER-VALUE'])
        data['PERCENTAGE-USED'] = (int(data['NUMBER-VALUE']) / eep_total_size) * 100

    eeprom_total_used_size = 0
    for data in data_ea:
        data['CRC-SIZE'] = EEPROM_Level1(int(data['NUMBER-VALUE']),data['SIZE-VALUE'])
        eeprom_total_used_size = eeprom_total_used_size + data['CRC-SIZE']
        data['CRC-PERCENTAGE-USED'] = (data['CRC-SIZE'] / eep_total_size) * 100

    #lvl 0
    #075
    eeprom_used_size_percentage = (eeprom_total_used_size / eep_total_size) * 100

    #lvl 2 este reprezentat de parsarea in_memconfig
    # print("FINAL DATA EEPROM............................")
    # for data in data_ea:
    #     print(data)
    # print("FINAL DATA EEPROM END........................")
    return data_ea,eeprom_total_used_size

def calcultate_dataflash(data_fee):
    # lvl 0
    #066
    DATAFLASHUsedMemory = 0
    for data in data_fee:
        DATAFLASHUsedMemory = DATAFLASHUsedMemory + int(data['NUMBER-VALUE'])
    # print('DATAFLASHUsedMemory: ' + str(DATAFLASHUsedMemory))

    #lvl 2
    #067
    block_groups = []
    for data in data_fee:
        obj = {}
        ok = 0
        if 'Fee_NvM_Block' in data['NAME']:
            if data['NAME'][-2] =="_":
                obj['NAME'] = data['NAME'][14:-2]
            else:
                if data['NAME'][-3] =="_":
                    obj['NAME'] = data['NAME'][14:-3]
            for block in block_groups:
                if obj['NAME'] in block['NAME']:
                    ok = 1
            if ok == 0:
                block_groups.append(obj)
    # print('DATAFLASH BLOCKS:')


    for block in block_groups:
        block_number_value = 0
        block_size_value = 0
        for data in data_fee:
            if block['NAME'] in data['NAME']:
                block_number_value = block_number_value + int(data['NUMBER-VALUE'])
                block_size_value = block_size_value + int(data['SIZE-VALUE'])
        block['NUMBER-VALUE'] = block_number_value
        block['SIZE-VALUE'] = block_size_value

    # for block in blocks:
    #     print(block)
    return DATAFLASHUsedMemory


def calculate_ram_rom(mapfile_path,rr_regions,logger):
    #17,21
    symbol_list = []
    for file in mapfile_path:
        parser = etree.XMLParser(remove_comments=True)
        tree = objectify.parse(file, parser=parser)
        root = tree.getroot()
        memory_region = root.findall(".//{http://www.hightec-rt.com/map/}Symbol")
        for data in memory_region:
            if data.getparent().tag == "{http://www.hightec-rt.com/map/}SymbolList":
                if 'ABS' not in data.attrib['memory'] :
                    obj = {}
                    obj['START'] = data.attrib['start']
                    obj['END'] = data.attrib['end']
                    obj['SIZE'] = int(data.attrib['size'])
                    obj['SCOPE'] = data.attrib['scope']
                    obj['NAME'] = data.attrib['name']
                    obj['MEMORY'] = data.attrib['memory']
                    obj['OUTPUT-SECTION'] = data.attrib['output_section']
                    obj['INPUT_SECTION'] = data.attrib['input_section']
                    symbol_list.append(obj)

    o_sections = []
    for file in mapfile_path:
        parser = etree.XMLParser(remove_comments=True)
        tree = objectify.parse(file, parser=parser)
        root = tree.getroot()
        outputs = root.findall(".//{http://www.hightec-rt.com/map/}OutputSection")
        for data in outputs:
            if data.getparent().tag == "{http://www.hightec-rt.com/map/}SectionList":
                try:
                    obj = {}
                    obj['NAME'] = data.attrib['name']
                    obj['MEMORY-REGION'] = data.attrib['memory_region']
                    obj['START'] = data.attrib['start']
                    obj['SIZE'] = data.attrib['size']
                    o_sections.append(obj)
                except:
                    pass

    # for section in o_sections:
    #     print(section)

    #18 = 26
    output_sections = []
    obj = {}
    obj['OUTPUT-SECTION'] = symbol_list[0]['OUTPUT-SECTION']
    output_sections.append(obj)

    for symbol in symbol_list:
        ok = 0
        for section in output_sections:
            obj = {}
            if symbol['OUTPUT-SECTION'] == section['OUTPUT-SECTION']:
                ok = 1
                break
        if ok == 0:
            obj['OUTPUT-SECTION'] = symbol['OUTPUT-SECTION']
            output_sections.append(obj)

    for section in output_sections:
        used_memory = 0
        for symbol in symbol_list:
            if symbol['OUTPUT-SECTION'] == section['OUTPUT-SECTION']:
                used_memory = used_memory + symbol['SIZE']
        section['USED-MEMORY'] = used_memory

    # print("OUTPUT_SECTIONS........................")
    # for section in output_sections:
    #     print(section)
    # print("END OF OUTPUT_SECTIONS........................")


    #13
    for s1 in output_sections:
        for s2 in o_sections:
            if s1['OUTPUT-SECTION'] == s2['NAME']:
                if s1['USED-MEMORY'] > int(s2['SIZE']):
                    print("ERROR, RAM/ROM MEMORY OVERLOAD " + s2['NAME'])
                    logger.error("ERROR, RAM/ROM MEMORY OVERLOAD " + s2['NAME'])



    #19
    scopes = []
    obj = {}
    obj['SCOPE'] = symbol_list[0]['SCOPE']
    scopes.append(obj)
    for symbol in symbol_list:
        ok = 0
        for scope in scopes:
            obj = {}
            if symbol['SCOPE'] == scope['SCOPE']:
                ok = 1
                break
        if ok == 0:
            obj['SCOPE'] = symbol['SCOPE']
            scopes.append(obj)

    for scope in scopes:
        cnt = 0
        str = ''
        for symbol in symbol_list:
            if symbol['SCOPE'] == scope['SCOPE']:
                cnt = cnt + 1
                str = str + " " + symbol['OUTPUT-SECTION']
        scope['VARIABLES'] = cnt
        scope['SECTIONS'] = str

    #22
    memory_regions = []
    for file in mapfile_path:
        parser = etree.XMLParser(remove_comments=True)
        tree = objectify.parse(file, parser=parser)
        root = tree.getroot()
        memory_region = root.findall(".//{http://www.hightec-rt.com/map/}MemoryRegion")
        for data in memory_region:
            if data.getparent().tag == "{http://www.hightec-rt.com/map/}MemoryConfiguration":
                if 'default' not in data.attrib['name']:
                    obj = {}
                    obj['NAME'] = data.attrib['name']
                    obj['ORIGIN'] = data.attrib['origin']
                    obj['LENGTH'] = int(data.attrib['length'],16)
                    obj['USED'] = int(data.attrib['used'],16)
                    obj['FREE'] = data.attrib['free']
                    memory_regions.append(obj)


    #26
    # section_memory = []
    # obj = {}
    # obj['SECTION'] = symbol_list[0]['OUTPUT-SECTION']
    # obj['REGION'] = symbol_list[0]['MEMORY']
    # section_memory.append(obj)
    # for symbol in symbol_list:
    #     ok = 0
    #     for data in section_memory:
    #         if symbol['OUTPUT-SECTION'] == data['SECTION'] and symbol['MEMORY'] == data['REGION']:
    #             ok = 1
    #             break
    #     if ok == 0:
    #         obj = {}
    #         obj['SECTION'] = symbol['OUTPUT-SECTION']
    #         obj['REGION'] = symbol['MEMORY']
    #         section_memory.append(obj)



    #27
    for region in memory_regions:
        size = 0
        for symbol in symbol_list:
            if symbol['MEMORY'] == region['NAME']:
                region['SECTION'] = symbol['OUTPUT-SECTION']
                if int(symbol['START'],16) > int(region['ORIGIN'],16) and int(symbol['END'],16) < (int(region['ORIGIN'],16) + region['LENGTH']):
                    size = size + symbol['SIZE']
                if int(symbol['START'], 16) < int(region['ORIGIN'], 16) or int(symbol['END'], 16) > (int(region['ORIGIN'], 16) + region['LENGTH']):
                    print("ERROR VARIABLE ADDRES OUT OF REGION " + symbol['NAME'])
                    logger.error("ERROR VARIABLE ADDRES OUT OF REGION " + symbol['NAME'])

        region['USED-CALCULATED'] = size
        # print(region)



    #28
    for region in memory_regions:
        #size = region['USED-CALCULATED'] + int(region['FREE'],16)
        region['USED-PERCENTAGE'] = (region['USED-CALCULATED'] / region['LENGTH']) * 100

    # print("MEMORY_REGIONS........................")
    # for region in memory_regions:
    #     print(region)
    # print("END OF MEMORY_REGIONS........................")

    # print("RR_REGIONS........................")
    # for region in rr_regions:
    #     print(region)
    # print("END OF RR_REGIONS........................")

    #009
    ram_memory = []
    rom_memory = []
    for region in rr_regions:
        if 'ram' in region['NAME']:
            obj = {}
            obj['NAME'] = region['NAME']
            obj['START-ADDRESS'] = region['START-ADDRESS']
            obj['END-ADDRESS'] = hex(int(region['START-ADDRESS'],16) + region['SIZE'])
            ram_memory.append(obj)
        if 'rom' in region['NAME']:
            obj = {}
            obj['NAME'] = region['NAME']
            obj['START-ADDRESS'] = region['START-ADDRESS']
            obj['END-ADDRESS'] = hex(int(region['START-ADDRESS'],16) + region['SIZE'])
            rom_memory.append(obj)

    # print("RAM MEMORY..................")
    # for ram in ram_memory:
    #     print(ram)
    # print("END OF RAM MEMORY.............")
    # print("ROM MEMORY..................")
    # for rom in rom_memory:
    #     print(rom)
    # print("END OF ROM MEMORY.............")

    #16
    variables_list = []
    for symbol in symbol_list:
        for ram in ram_memory:
            if symbol['MEMORY'] == ram['NAME']:
                obj = {}
                obj['NAME'] = symbol['NAME']
                obj['TYPE'] = 'RAM'
                obj['REGION'] = ram['NAME']
                obj['SIZE'] = symbol['SIZE']
                obj['SECTION'] = symbol['OUTPUT-SECTION']
                obj['SCOPE'] = symbol['SCOPE']
                variables_list.append(obj)
                break
        for rom in rom_memory:
            if symbol['MEMORY'] == rom['NAME']:
                obj = {}
                obj['NAME'] = symbol['NAME']
                obj['TYPE'] = 'ROM'
                obj['REGION'] = rom['NAME']
                obj['SIZE'] = symbol['SIZE']
                obj['SECTION'] = symbol['OUTPUT-SECTION']
                obj['SCOPE'] = symbol['SCOPE']
                variables_list.append(obj)
                break




    for section in output_sections:
        ram_size = 0
        rom_size = 0
        for variable in variables_list:
            if section['OUTPUT-SECTION'] == variable['SECTION']:
                if variable['TYPE'] =='RAM':
                    ram_size = ram_size + variable['SIZE']
                if variable['TYPE'] =='ROM':
                    rom_size = rom_size + variable['SIZE']
        section['RAM-MEMORY'] = ram_size
        section['ROM-MEMORY'] = rom_size

    # for section in output_sections:
    #     for variable in variables_list:
    #         if variable['SECTION'] == section['OUTPUT-SECTION']:
    #             for scope in scopes:
    #                 if variable['SCOPE'] ==




    return scopes,symbol_list,memory_regions,output_sections,ram_memory,rom_memory,variables_list,o_sections



#12
def verify_map_ld(memory_regions, regions,logger):
    for r1 in memory_regions:
        for r2 in regions:
            if r1['NAME'] == r2['NAME']:
                if int(r1['ORIGIN'],16) != int(r2['START-ADDRESS'],16) or r1['LENGTH'] != r2['SIZE']:
                    print("ERROR - DIFFERENT MEMORY RANGES IN MAPFILE AND LDSCRIPT")
                    logger.error("ERROR - DIFFERENT MEMORY RANGES IN MAPFILE AND LDSCRIPT")
                    return False
                break
    return True


def in_dep(dep_path):
    for path in dep_path:
        file = open(path)
        line = file.readline()
        line = file.readline()
        line = line.strip()

def create_excel(scopes,symbol_list,memory_regions,output_sections,ram_memory,rom_memory,variables_list,o_sections,data_fee,DataflashUsed,eep_total_size, data_eeprom,eeprom_total_used_size,eeprom_blocks,modules,outputxlsx,data_flash,total_dataflash):
    wb = Workbook()
    ws1 = wb.new_sheet("Header")
    ws2 = wb.new_sheet("Level0")
    ws3 = wb.new_sheet("ROM_RAM_SectionLevel")
    ws4 = wb.new_sheet("ROM_RAM_RegionLevel")
    ws5 = wb.new_sheet("ROM_RAM_FileLevel")
    ws6 = wb.new_sheet("ROM_RAM_ModuleLevel")
    ws7 = wb.new_sheet("ROM_RAM_ContributorLevel")
    ws8 = wb.new_sheet("DATAFLASH_BlockLevel")
    ws9 = wb.new_sheet("DATAFLASH_Module_Level")
    ws10 = wb.new_sheet("EEPROM_BlockLevel")
    ws11 = wb.new_sheet("EEPROM_ProfileLevel")
    ws12 = wb.new_sheet("EEPROM_ModuleLevel")


    ws1.cell("B2").value = 'Document'
    ws1.cell("B2").style.font.bold = True
    ws1.cell("B3").value = 'Project'
    ws1.cell("B3").style.font.bold = True
    ws1.cell("B4").value = 'Team'
    ws1.cell("B4").style.font.bold = True
    ws1.cell("B5").value = 'Version'
    ws1.cell("B5").style.font.bold = True
    ws1.cell("B6").value = 'Author'
    ws1.cell("B6").style.font.bold = True
    ws1.cell("B7").value = 'Current SW Version'
    ws1.cell("B7").style.font.bold = True
    ws1.cell("A9").value = 'Action List'
    ws1.cell("A9").style.font.color = Color(255, 0, 0)

    ws1.cell("B10").value = 'Date'
    ws1.cell("B10").style.font.bold = True
    ws1.cell("C10").value = 'Action'
    ws1.cell("C10").style.font.bold = True
    ws1.cell("D10").value = 'Author'
    ws1.cell("D10").style.font.bold = True
    ws1.cell("E10").value = 'Version'
    ws1.cell("E10").style.font.bold = True



    ws2.set_col_style(2, Style(size=-1))
    ws2.set_col_style(1, Style(size=-1))
    ws2.set_col_style(3, Style(size=-1))
    #ws2.set_col_style(4, Style(size=-1))
    ws2.set_col_style(5, Style(size=-1))
    ws2.set_col_style(6, Style(size=-1))
    ws2.set_col_style(7, Style(size=100))
    ws2.set_col_style(8, Style(size=-1))
    ws2.set_col_style(9, Style(size=-1))
    ws2.set_col_style(10, Style(size=-1))
    ws2.set_col_style(11, Style(size=-1))
    ws2.set_col_style(12, Style(size=-1))
    ws2.set_col_style(13, Style(size=0))
    ws2.set_col_style(14, Style(size=-1))
    ws2.set_col_style(15, Style(size=-1))
    ws2.set_col_style(16, Style(size=-1))
    ws2.set_col_style(17, Style(size=-1))
    ws2.set_col_style(18, Style(size=-1))
    #ws2.cell("G").style.font.color = Color(255, 255, 255)
    ws2.set_col_style(7, Style(fill=Fill(background=Color(0, 0, 0))))
    ws2.set_col_style(13, Style(fill=Fill(background=Color(0, 0, 0))))
    ws2.cell("A2").style.font.color = Color(255, 0, 0)
    ws2.cell("H2").style.font.color = Color(255, 0, 0)
    ws2.cell("N2").style.font.color = Color(255, 0, 0)


    ws2.range("A2","F2").merge()
    ws2.cell("A2").value = 'All memories results'
    ws2.range("A2","F2").style.alignment.wrap_text = True
    ws2.cell("A4").value = 'Memory'
    ws2.cell("A4").style.font.bold = True
    ws2.cell("B4").value = 'StartAddress'
    ws2.cell("B4").style.font.bold = True
    ws2.cell("C4").value = 'EndAddress'
    ws2.cell("C4").style.font.bold = True
    ws2.cell("D4").value = 'Size'
    ws2.cell("D4").style.font.bold = True
    ws2.cell("E4").value = 'TotalUsedSize'
    ws2.cell("E4").style.font.bold = True
    ws2.cell("F4").value = 'UsedPercentage'
    ws2.cell("F4").style.font.bold = True
    ws2.cell("A5").value = 'ROM'
    ws2.cell("A6").value = 'RAM'
    ws2.cell("A7").value = 'EEPROM'
    ws2.cell("A8").value = 'DATAFLASH'

    ws2.range("H2", "L2").merge()
    ws2.cell("H2").value = 'Biggest RAM consumers'
    ws2.range("H2", "L2").style.alignment.wrap_text = True
    ws2.cell("H4").value = 'FileName'
    ws2.cell("H4").style.font.bold = True
    ws2.cell("I4").value = 'Module'
    ws2.cell("I4").style.font.bold = True
    ws2.cell("J4").value = 'Contributor'
    ws2.cell("J4").style.font.bold = True
    ws2.cell("K4").value = 'UsedRAMSize'
    ws2.cell("K4").style.font.bold = True
    ws2.cell("L4").value = 'UsedRAMPercentage'
    ws2.cell("L4").style.font.bold = True

    ws2.range("N2", "R2").merge()
    ws2.cell("N2").value = 'Biggest ROM consumers'
    ws2.range("N2", "R2").style.alignment.wrap_text = True
    ws2.cell("N4").value = 'FileName'
    ws2.cell("N4").style.font.bold = True
    ws2.cell("O4").value = 'Module'
    ws2.cell("O4").style.font.bold = True
    ws2.cell("P4").value = 'Contributor'
    ws2.cell("P4").style.font.bold = True
    ws2.cell("Q4").value = 'UsedROMSize'
    ws2.cell("Q4").style.font.bold = True
    ws2.cell("R4").value = 'UsedROMPercentage'
    ws2.cell("R4").style.font.bold = True


    ws3.cell("A1").value = 'SectionName'
    ws3.cell("A1").style.font.bold = True
    ws3.set_col_style(1, Style(size=-1))
    ws3.cell("B1").value = 'RAMUsedSize'
    ws3.cell("B1").style.font.bold = True
    ws3.set_col_style(2, Style(size=-1))
    ws3.cell("C1").value = 'RAMUsedPercentage'
    ws3.cell("C1").style.font.bold = True
    ws3.set_col_style(3, Style(size=-1))
    ws3.cell("D1").value = 'ROMUsedSize'
    ws3.cell("D1").style.font.bold = True
    ws3.set_col_style(4, Style(size=-1))
    ws3.cell("E1").value = 'ROMUsedPercentage'
    ws3.cell("E1").style.font.bold = True
    ws3.set_col_style(5, Style(size=-1))
    i = 6
    for scope in scopes:
        ws3[1][i].value = 'NumberOf ' + scope['SCOPE'] + ' Variables'
        ws3[1][i].style.font.bold = True
        ws3.set_col_style(i, Style(size=-1))
        i = i + 1


    ws4.cell("A1").value = 'RegionName'
    ws4.cell("A1").style.font.bold = True
    ws4.set_col_style(1, Style(size=-1))
    ws4.cell("B1").value = 'StartAddress'
    ws4.cell("B1").style.font.bold = True
    ws4.set_col_style(2, Style(size=-1))
    ws4.cell("C1").value = 'EndAddress'
    ws4.cell("C1").style.font.bold = True
    ws4.set_col_style(3, Style(size=-1))
    ws4.cell("D1").value = 'Size'
    ws4.cell("D1").style.font.bold = True
    ws4.set_col_style(4, Style(size=-1))
    ws4.cell("E1").value = 'UsedMemory'
    ws4.cell("E1").style.font.bold = True
    ws4.set_col_style(5, Style(size=-1))
    ws4.cell("F1").value = 'Usage Percentage'
    ws4.cell("F1").style.font.bold = True
    ws4.set_col_style(6, Style(size=-1))

    i = 7
    for section in output_sections:
        ws4[1][i].value = section['OUTPUT-SECTION'] + ' UsedSize'
        ws4[1][i].style.font.bold = True
        ws4.set_col_style(i, Style(size=-1))
        i = i + 1

    for scope in scopes:
        ws4[1][i].value = 'NumberOf' + scope['SCOPE'] + ' Variables'
        ws4[1][i].style.font.bold = True
        ws4.set_col_style(i, Style(size=-1))
        i = i + 1


    ws5.cell("A1").value = 'FileName'
    ws5.cell("A1").style.font.bold = True
    ws5.set_col_style(1, Style(size=-1))
    ws5.cell("B1").value = 'Module'
    ws5.cell("B1").style.font.bold = True
    ws5.set_col_style(2, Style(size=-1))
    ws5.cell("C1").value = 'Contributor'
    ws5.cell("C1").style.font.bold = True
    ws5.set_col_style(3, Style(size=-1))
    ws5.cell("D1").value = 'RAMUsedSize'
    ws5.cell("D1").style.font.bold = True
    ws5.set_col_style(4, Style(size=-1))
    ws5.cell("E1").value = 'RAMUsedPercentage'
    ws5.cell("E1").style.font.bold = True
    ws5.set_col_style(5, Style(size=-1))
    ws5.cell("F1").value = 'ROMUsedSize'
    ws5.cell("F1").style.font.bold = True
    ws5.set_col_style(6, Style(size=-1))
    ws5.cell("G1").value = 'ROMUsedPercentage'
    ws5.cell("G1").style.font.bold = True
    ws5.set_col_style(7, Style(size=-1))

    i = 8
    for section in output_sections:
        ws5[1][i].value = section['OUTPUT-SECTION'] + ' UsedSize'
        ws5[1][i].style.font.bold = True
        ws5.set_col_style(i, Style(size=-1))
        i = i + 1

    for scope in scopes:
        ws5[1][i].value = 'NumberOf ' + scope['SCOPE'] + ' Variables'
        ws5[1][i].style.font.bold = True
        ws5.set_col_style(i, Style(size=-1))
        i = i + 1


    ws6.cell("A1").value = 'ModuleName'
    ws6.cell("A1").style.font.bold = True
    ws6.set_col_style(1, Style(size=-1))
    ws6.cell("B1").value = 'Contributor'
    ws6.cell("B1").style.font.bold = True
    ws6.set_col_style(2, Style(size=-1))
    ws6.cell("C1").value = 'RAMUsedSize'
    ws6.cell("C1").style.font.bold = True
    ws6.set_col_style(3, Style(size=-1))
    ws6.cell("D1").value = 'RAMUsedPercentage'
    ws6.cell("D1").style.font.bold = True
    ws6.set_col_style(4, Style(size=-1))
    ws6.cell("E1").value = 'ROMUsedSize'
    ws6.cell("E1").style.font.bold = True
    ws6.set_col_style(5, Style(size=-1))
    ws6.cell("F1").value = 'ROMUsedPercentage'
    ws6.cell("F1").style.font.bold = True
    ws6.set_col_style(6, Style(size=-1))
    ws6.cell("G1").value = 'NumberOfFiles'
    ws6.cell("G1").style.font.bold = True
    ws6.set_col_style(7, Style(size=-1))

    i = 8
    for section in output_sections:
        ws6[1][i].value = section['OUTPUT-SECTION'] + ' UsedSize'
        ws6[1][i].style.font.bold = True
        ws6.set_col_style(i, Style(size=-1))
        i = i + 1

    for scope in scopes:
        ws6[1][i].value = 'NumberOf ' + scope['SCOPE'] + ' Variables'
        ws6[1][i].style.font.bold = True
        ws6.set_col_style(i, Style(size=-1))
        i = i + 1


    ws7.cell("A1").value = 'ContributorName'
    ws7.cell("A1").style.font.bold = True
    ws7.set_col_style(1, Style(size=-1))
    ws7.cell("B1").value = 'RAMUsedSize'
    ws7.cell("B1").style.font.bold = True
    ws7.set_col_style(2, Style(size=-1))
    ws7.cell("C1").value = 'RAMUsedPercentage'
    ws7.cell("C1").style.font.bold = True
    ws7.set_col_style(3, Style(size=-1))
    ws7.cell("D1").value = 'ROMUsedSize'
    ws7.cell("D1").style.font.bold = True
    ws7.set_col_style(4, Style(size=-1))
    ws7.cell("E1").value = 'ROMUsedPercentage'
    ws7.cell("E1").style.font.bold = True
    ws7.set_col_style(5, Style(size=-1))
    ws7.cell("F1").value = 'NumberOfFiles'
    ws7.cell("F1").style.font.bold = True
    ws7.set_col_style(6, Style(size=-1))
    ws7.cell("G1").value = 'NumberOfModules'
    ws7.cell("G1").style.font.bold = True
    ws7.set_col_style(7, Style(size=-1))

    i = 8
    for section in output_sections:
        ws7[1][i].value = section['OUTPUT-SECTION'] + ' UsedSize'
        ws7[1][i].style.font.bold = True
        ws7.set_col_style(i, Style(size=-1))
        i = i + 1

    for scope in scopes:
        ws7[1][i].value = 'NumberOf ' + scope['SCOPE'] + ' Variables'
        ws7[1][i].style.font.bold = True
        ws7.set_col_style(i, Style(size=-1))
        i = i + 1

    ws8.cell("A1").value = 'BlockName'
    ws8.cell("A1").style.font.bold = True
    ws8.set_col_style(1, Style(size=-1))
    ws8.cell("B1").value = 'StartAddress'
    ws8.cell("B1").style.font.bold = True
    ws8.set_col_style(2, Style(size=-1))
    ws8.cell("C1").value = 'EndAddress'
    ws8.cell("C1").style.font.bold = True
    ws8.set_col_style(3, Style(size=-1))
    ws8.cell("D1").value = 'BlockSize'
    ws8.cell("D1").style.font.bold = True
    ws8.set_col_style(4, Style(size=-1))
    ws8.cell("E1").value = 'DATAFLASHUsedPercentage'
    ws8.cell("E1").style.font.bold = True
    ws8.set_col_style(5, Style(size=-1))


    ws9.cell("A1").value = 'ModelName'
    ws9.cell("A1").style.font.bold = True
    ws9.set_col_style(1, Style(size=-1))
    ws9.cell("B1").value = 'Contributor'
    ws9.cell("B1").style.font.bold = True
    ws9.set_col_style(2, Style(size=-1))
    ws9.cell("C1").value = 'NumberOfBlocks'
    ws9.cell("C1").style.font.bold = True
    ws9.set_col_style(3, Style(size=-1))
    ws9.cell("D1").value = 'UsedSize'
    ws9.cell("D1").style.font.bold = True
    ws9.set_col_style(4, Style(size=-1))
    ws9.cell("E1").value = 'DATAFLASHUsedPercentage'
    ws9.cell("E1").style.font.bold = True
    ws9.set_col_style(5, Style(size=-1))


    ws10.cell("A1").value = 'BlockName'
    ws10.cell("A1").style.font.bold = True
    ws10.set_col_style(1, Style(size=-1))
    ws10.cell("B1").value = 'StartAddress'
    ws10.cell("B1").style.font.bold = True
    ws10.set_col_style(2, Style(size=-1))
    ws10.cell("C1").value = 'EndAddress'
    ws10.cell("C1").style.font.bold = True
    ws10.set_col_style(3, Style(size=-1))
    ws10.cell("D1").value = 'BlockSize'
    ws10.cell("D1").style.font.bold = True
    ws10.set_col_style(4, Style(size=-1))
    ws10.cell("E1").value = 'EEPROMUsedPercentage'
    ws10.cell("E1").style.font.bold = True
    ws10.set_col_style(5, Style(size=-1))


    ws11.cell("A1").value = 'ProfileName'
    ws11.cell("A1").style.font.bold = True
    ws11.set_col_style(1, Style(size=-1))
    ws11.cell("B1").value = 'NumberOfBlocks'
    ws11.cell("B1").style.font.bold = True
    ws11.set_col_style(2, Style(size=-1))
    ws11.cell("C1").value = 'UsedSize'
    ws11.cell("C1").style.font.bold = True
    ws11.set_col_style(3, Style(size=-1))
    ws11.cell("D1").value = 'DTAFLASHUsedPercentage'
    ws11.cell("D1").style.font.bold = True
    ws11.set_col_style(4, Style(size=-1))


    ws12.cell("A1").value = 'ModuleName'
    ws12.cell("A1").style.font.bold = True
    ws12.set_col_style(1, Style(size=-1))
    ws12.cell("B1").value = 'Contributor'
    ws12.cell("B1").style.font.bold = True
    ws12.set_col_style(2, Style(size=-1))
    ws12.cell("C1").value = 'NumberOfBlocks'
    ws12.cell("C1").style.font.bold = True
    ws12.set_col_style(3, Style(size=-1))
    ws12.cell("D1").value = 'NumberOfProfiles'
    ws12.cell("D1").style.font.bold = True
    ws12.set_col_style(4, Style(size=-1))
    ws12.cell("E1").value = 'UsedSize'
    ws12.cell("E1").style.font.bold = True
    ws12.set_col_style(5, Style(size=-1))
    ws12.cell("F1").value = 'EEPROMUsedPercentage'
    ws12.cell("F1").style.font.bold = True
    ws12.set_col_style(6, Style(size=-1))

    ram_used_memory = 0
    rom_used_memory = 0
    for variable in variables_list:
        if variable['TYPE'] == 'RAM':
            ram_used_memory = ram_used_memory + variable['SIZE']
        if variable['TYPE'] == 'ROM':
            rom_used_memory = rom_used_memory + variable['SIZE']
    ws2.cell("E5").value = rom_used_memory
    ws2.cell("E6").value = ram_used_memory

    min_rom = rom_memory[0]['START-ADDRESS']
    max_rom = rom_memory[0]['END-ADDRESS']
    for rom in rom_memory:
        if min_rom > rom['START-ADDRESS']:
            min_rom = rom['START-ADDRESS']
        if max_rom < rom['END-ADDRESS']:
            max_rom = rom['END-ADDRESS']
    ws2.cell("B5").value = min_rom
    ws2.cell("C5").value = max_rom
    ws2.cell("D5").value = int(max_rom,16) - int(min_rom,16)
    ws2.cell("F5").value = round((rom_used_memory / (int(max_rom, 16) - int(min_rom, 16))) * 100,2)

    min_ram = ram_memory[0]['START-ADDRESS']
    max_ram = ram_memory[0]['END-ADDRESS']
    for ram in ram_memory:
        if min_ram > ram['START-ADDRESS']:
            min_ram = ram['START-ADDRESS']
        if max_ram < ram['END-ADDRESS']:
            max_ram = ram['END-ADDRESS']
    ws2.cell("B6").value = min_ram
    ws2.cell("C6").value = max_ram
    ws2.cell("D6").value = int(max_ram,16) - int(min_ram,16)
    ws2.cell("F6").value = round((ram_used_memory / (int(max_ram, 16) - int(min_ram, 16))) * 100,2)

    ws2.cell("D7").value = eep_total_size
    ws2.cell("E7").value = eeprom_total_used_size
    ws2.cell("F7").value = round((eeprom_total_used_size / eep_total_size) * 100,2)

    ws2.cell("B8").value = data_flash[0]['START']
    a = len(data_flash)
    ws2.cell("C8").value = data_flash[a-1]['END']
    ws2.cell("D8").value = total_dataflash
    ws2.cell("E8").value = DataflashUsed
    ws2.cell("F8").value = round((DataflashUsed / total_dataflash) * 100, 2)

    #Ram_Rom_Section_Level
    section_scopes = []
    for output in output_sections:
        obj = {}
        obj['SECTION'] = output['OUTPUT-SECTION']
        section_scopes.append(obj)

    for ss in section_scopes:
        for symbol in symbol_list:
            if ss['SECTION'] == symbol['OUTPUT-SECTION']:
               if symbol['SCOPE'] not in ss:
                   ss[symbol['SCOPE']] = 1
               if symbol['SCOPE'] in ss:
                   ss[symbol['SCOPE']] = ss[symbol['SCOPE']] + 1

    i=2
    j=0
    nr_scopes = 5 + len(scopes)

    for section in output_sections:
        col = 6
        ws3[i][1].value = section['OUTPUT-SECTION']
        ws3[i][2].value = section['RAM-MEMORY']
        ws3[i][4].value = section['ROM-MEMORY']
        ws3[i][3].value = round((section['RAM-MEMORY'] / ram_used_memory) * 100,2)
        ws3[i][5].value = round((section['ROM-MEMORY'] / rom_used_memory) * 100,2)
        for r in range(len(scopes)):
            for x, y in section_scopes[j].items():
                if x in ws3[1][col+r].value:
                    ws3[i][col+r].value = y
                    break
                else:
                    ws3[i][col+r].value = 0

        j = j + 1
        i = i + 1


    #ROM_RAM_REGION_LEVEL

    region_sections = []
    for region in memory_regions:
        obj = {}
        obj['REGION'] = region['NAME']
        region_sections.append(obj)
        for rs in region_sections:
            for symbol in symbol_list:
                if rs['REGION'] == symbol['MEMORY']:
                   if symbol['OUTPUT-SECTION'] not in rs:
                       rs[symbol['OUTPUT-SECTION']] = symbol['SIZE']
                   if symbol['OUTPUT-SECTION'] in rs:
                       rs[symbol['OUTPUT-SECTION']] = rs[symbol['OUTPUT-SECTION']] + symbol['SIZE']

    for rs in region_sections:
        for symbol in symbol_list:
            if rs['REGION'] == symbol['MEMORY']:
               if symbol['SCOPE'] not in rs:
                   rs[symbol['SCOPE']] = 1
               if symbol['SCOPE'] in rs:
                   rs[symbol['SCOPE']] = rs[symbol['SCOPE']] + 1


    i = 2
    col = 7
    j = 0
    for region in memory_regions:
        ws4[i][1].value = region['NAME']
        ws4[i][2].value = region['ORIGIN']
        ws4[i][3].value = hex(int(region['ORIGIN'],16) + region['LENGTH'])
        ws4[i][4].value = region['LENGTH']
        ws4[i][5].value = region['USED-CALCULATED']
        ws4[i][6].value = round(region['USED-PERCENTAGE'],2)
        for r in range(len(output_sections)):
            for x,y in region_sections[j].items():
                    if x in ws4[1][7+r].value:
                        ws4[i][r+7] = y
                        break
                    else:
                        ws4[i][r + 7] = 0
        for q in range(len(scopes)):
            for x, y in region_sections[j].items():
                if x in ws4[1][col+r+q+1].value:
                    ws4[i][col+r+q+1].value = y
                    break
                else:
                    ws4[i][col+r+q+1].value = 0
        j = j + 1
        i = i + 1


    #DATALFASH_BLOCKLEVEL
    i = 2

    for block in data_fee:
        ws8[i][1].value = block['NAME']
        ws8[i][4].value = block['NUMBER-VALUE']
        ws8[i][5].value = round((int(block['NUMBER-VALUE']) / DataflashUsed) * 100,2)
        i = i + 1


    #EEPROM_BLOCKLEVEL
    i=2
    for data in data_eeprom:
        ws10[i][1] = data['NAME']
        ws10[i][4] = data['CRC-SIZE']
        ws10[i][5] = round(data['CRC-PERCENTAGE-USED'],2)
        i = i + 1


    #EEPROM_PROFILELEVEL
    profile_blocks = []
    obj = {}
    obj['PROFILE'] = eeprom_blocks[0]['REF']
    profile_blocks.append(obj)
    for block in eeprom_blocks:
        ok = 0
        for profile in profile_blocks:
            if profile['PROFILE'] == block['REF']:
                ok = 1
        if ok == 0:
            obj = {}
            obj['PROFILE'] = block['REF']
            profile_blocks.append(obj)

    for profile in profile_blocks:
        cnt = 0
        for block in eeprom_blocks:
            if profile['PROFILE'] == block['REF']:
                cnt = cnt + 1
        profile['NUMBER'] = cnt

    i = 2
    for profile in profile_blocks:
        ws11[i][1] = profile['PROFILE']
        ws11[i][2] = profile['NUMBER']
        i = i + 1

    #EEPROM_MODULELEVEL
    module_names = []
    obj= {}
    obj['MODULE-NAME'] = modules[0]['NAME'].split("/")[1][6:]
    module_names.append(obj)
    for module in modules:
        ok = 0
        for mn in module_names:
            if module['NAME'].split("/")[1][6:] == mn['MODULE-NAME']:
                ok = 1
                break
        if ok == 0:
            obj = {}
            obj['MODULE-NAME'] = module['NAME'].split("/")[1][6:]
            module_names.append(obj)

    for mn in module_names:
        cnt = 0
        list = []
        for module in modules:
            if module['NAME'].split("/")[1][6:] == mn['MODULE-NAME']:
                if module['BLOCK'] not in list:
                    cnt = cnt + 1
                    list.append(module['BLOCK'])
        mn['BLOCK-OCCURENCE'] = cnt

    for mn in module_names:
        cnt = 0
        list = []
        for module in modules:
            if module['NAME'].split("/")[1][6:] == mn['MODULE-NAME']:
                if module['PROFILE'] not in list:
                    cnt = cnt + 1
                    list.append(module['PROFILE'])
        mn['PROFILE-OCCURENCE'] = cnt

    i = 2
    for mn in module_names:
        ws12[i][1] = mn['MODULE-NAME']
        ws12[i][3] = mn['BLOCK-OCCURENCE']
        ws12[i][4] = mn['PROFILE-OCCURENCE']
        i = i + 1


    wb.save(outputxlsx + "/Output.xlsx")

    return profile_blocks,min_rom,max_rom,min_ram,max_ram


if __name__ == "__main__":
    main()
# regex for ldscript
# \w+\s+: org = 0[xX][0-9a-fA-f]+, len = [0-9(*]+(k)*( - [()0-9*]+)*

