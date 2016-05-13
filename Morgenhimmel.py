#!/usr/bin/env python jezebel
# -*- coding: utf-8 -*-
#
# rh: 2009-10_02
# rh: 2014-03_29   vs 0.2
# rh: 2016-04_09   vs 0.3
#
# 497 Bilder, alle 4000 px * 3000 px // 496 = 2**4 * 31 == perfect number.
# 16*(4000 + 2*border) * 31*(3000 + 2*border) ==  64000 * 93000 + (32 * border)
#
# Version um:
# 1. die Morgenphotos umzubenennen: YYYY_MM_DD_HH_mm_SS_IMGxxxx.jpg
# 2. Belichtungszeit, FNumber und ISOSpeed zu extrahieren
# 3. CSV File zu erstellen mit fn, Uhrzeit, ExpoTime, F und ISOSpeed
# 4. Fehlende Bilder ersetzen
#
# Output:
# 1. neuen Filenamen samt Path
# 2. (Batchfile)
#
# https://pypi.python.org/pypi/ExifRead
#
## Für jedes Bild soll ein Objekt (iS eines -> data members) angelegt werden, das in einer Liste landet.
## Listen von Data member kann man auch gut sortieren:
##   http://stackoverflow.com/questions/403421/how-to-sort-a-list-of-objects-in-python-based-on-an-attribute-of-the-objects
## Dicts und Listen von DIcts kann man auch gut sortieren:
## https://wiki.python.org/moin/HowTo/Sorting  -> 'itemgetter' !!
##
## TODO list of pictures:
## stich pic's together
## http://stackoverflow.com/questions/10657383/stitching-photos-together
## Geht mit pil

import csv
import datetime
import exifread       # EXIF write python 2.7xx
import getopt
import io
import matplotlib.pyplot as plt
import numpy
import os
import piexif         # EXIF write python 2.7xx
import pprint
import random
import re
import scipy
import sys
import tempfile
from operator import itemgetter, attrgetter, methodcaller
from fractions import Fraction

# https://books.google.de/books?id=YRHSCgAAQBAJ&pg=PA96&lpg=PA96&dq=pil+average+grayscale&source=bl&ots=tsJ8nbYvua&sig=OHKPOAlTMV08S-p5jS-t_RacTS0&hl=de&sa=X&ved=0ahUKEwjrxo2I2JHMAhWEJhoKHY_rB0cQ6AEIRzAE#v=onepage&q=pil%20average%20grayscale&f=false
import numpy as np
from PIL import Image

path_root       = "D:\Data_Work\Other_Data\_Morgen_Himmel"
path_sub_pics   = "_Morgen_Himmel_alle_001"
path_sub_DWD    = "Data_DWD"

# just a little bit confusing those many interweaved paths:
root_dir        = 'D:\Data_Work\Other_Data\_Morgen_Himmel\_Morgen_Himmel_alle_001'
synth_image_dir = 'synth_images'
synth_image_dir = ''

quiet          = True
date_start     = '2013_04_07'  # 20130407
date_end       = '2014_08_16'  # 20140816

list_of_pict   = []
List_FNumbers  = []
List_ExpoTimes = []
List_ISOSpeeds = []

List_FNumbers_float  = []
List_ExpoTimes_float = []
List_ISOSpeeds_float = []

res_image      = None
res_curves     = None
res_figures    = None

x_cnt_pct      = 16
y_cnt_pct      = 31

x_pict_org     = 4000 # original picture
y_pict_org     = 3000 # original picture

scale_factor   = 3
border         = 2 * 3 * 4 * 5              # = 120
border         = border // scale_factor
x_pict         = x_pict_org // scale_factor # pixels on x-axis of single pict
y_pict         = y_pict_org // scale_factor # pixels on y-axis of single pict

# img == result image
x_img_dim      = (x_cnt_pct * x_pict) + (x_cnt_pct * border) + 3 * border # pixels on x-axis of result image
y_img_dim      = (y_cnt_pct * y_pict) + (y_cnt_pct * border) + 3 * border # pixels on y-axis of result image

# show command line usage
def usage(exit_status):
    msg = 'Usage: Photos_Rename.py [OPTIONS] \n'
    msg += 'Extract EXif information from JPEG files.\n'
    msg += 'Creates >rename_photos.bat< to rename pictures with hhmm-prefix \n'
    msg += 'i.e. hour and minute of exposure\n'
    msg += '\n'
    msg += 'Options:\n'
    msg += '  -v --verbose  verbose.\n'
    msg += '  -a --avrge    calc average gray value.\n'
    msg += '  -s --syn      synthesize new images\n'
    msg += '  -q --quiet    quiet (default)\n'
    msg += '\n'
    print msg
    if exit_status:
        sys.exit(exit_status)

def get_opts_args():
    global root_dir
    global quiet
    global do_calc_average
    global do_make_rename_file
    global batch_file
    global batch_f_name
    quiet = True

    try:
        #  >:< option requires argument
        opts, args = getopt.getopt(sys.argv[1:], "abhvqs", ["avrge", "batch", "verbose", "quiet", "syn"])
    except getopt.GetoptError:
        usage(2)
    if not args:
        usage(0)

    for o, a in opts:
        if o in ("-a", "--avrge"):
            do_calc_average = True
        if o in ("-b", "--batch"):
            do_make_rename_file = True
        if o in ("-s", "--syn"):
            do_make_new_images = True
        if o in ("-w", "--write_files"):
            do_write_files = True
        if o in ("-h", "--help"):
            usage(0)

    if not root_dir:
        root_dir = '.'

    if not quiet:
        print 'root_dir: >' + root_dir + '<'
    if not os.path.isdir(root_dir):
        print 'Directory >' + root_dir + '< does not exist.'
        sys.exit(2)

    if do_make_rename_file:
        try:
            batch_f_name = 'rename_photos.bat'
            batch_f_name = os.path.join(root_dir, batch_f_name)
            batch_file = open(batch_f_name, 'wb')
        except:
            print "'%s' is unwritable\n" % batch_f_name
            sys.exit(2)

    return quiet, do_calc_average, do_make_rename_file

# http://www.tutorialspoint.com/python/python_classes_objects.htm
class PictClass(object):
    def __init__(self, param):
        if type (param) == str: # param == datum
            datum = param
            self.cnt          = '0'
            self.datum        = datum
            self.Make         = 'rh'
            self.Model        = 'ToDo'
            self.date         = ''
            self.fn           = datum + '_' + '0900_IMG_rh.JPG'
            self.fn_old       = '0900_IMG_rh.JPG'         # default
            self.path_fn      = ''
            self.sources      = ''
            self.FNumber_str  = ''
            self.FNumber      = ''
            self.ExpoTime_str = ''
            self.ExpoTime     = ''
            self.ISOSpeed     = ''
            self.ISOSpeed_str = ''
            self.av_gray      = '-999.0'
            self.temperature  = ''
            self.humidity     = ''
            self.sky_KW_J     = '' #HIMMEL_KW_J
            self.global_KW_J  = '' #GLOBAL_KW_J
            self.atmo_KW_J    = '' #ATMOSPHAERE_LW_J
            self.sun_zenit    = '' #SONNENZENIT
            self.sources      = ''
            self.x_coord      = '' # x_coord in result_image
            self.y_coord      = '' # y_coord in result_image
            self.av_gray_y    = ''
            self.temperature_y= ''
            self.humidity_y   = ''
            self.sky_KW_J_y   = '' #HIMMEL_KW_J
            self.global_KW_J_y= '' #GLOBAL_KW_J
            self.atmo_KW_J_y  = '' #ATMOSPHAERE_LW_J
            self.sun_zenit_y  = '' #SONNENZENIT
            # self.xxxxxxx     = ''
            # self.xxxxxxx     = ''

        elif type (param) == dict:  # when reading from csv-file initialize >pict< with dict.
            dct = param
            for k, v in dct.items():
                setattr(self, k, v)
        else:
            print '>pict< cannot be initialized with type: >' + type(param) + '< .'
            sys.exit(2)

    def __repr__(self):
        return '%s; '*31 % (
        self.cnt          ,
        self.datum        ,
        self.Make         ,
        self.Model        ,
        self.date         ,
        self.fn           ,
        self.fn_old       ,
        self.path_fn      ,
        self.sources      ,
        self.FNumber_str  ,
        self.FNumber      ,
        self.ExpoTime_str ,
        self.ExpoTime     ,
        self.ISOSpeed     ,
        self.ISOSpeed_str ,
        self.av_gray      ,
        self.temperature  ,
        self.humidity     ,
        self.sky_KW_J     ,
        self.global_KW_J  ,
        self.atmo_KW_J    ,
        self.sun_zenit    ,
        self.x_coord      ,
        self.y_coord      ,
        self.av_gray_y    ,
        self.temperature_y,
        self.humidity_y   ,
        self.sky_KW_J_y   ,
        self.global_KW_J_y,
        self.atmo_KW_J_y  ,
        self.sun_zenit_y
        )

    fieldnames = [ "cnt",                 # used in: >picts_csv_write()< writing dict
        "datum", "Make", "Model",
        "date", "fn", "fn_old", "path_fn",
        "sources",
        "FNumber_str" , "FNumber",
        "ExpoTime_str", "ExpoTime",
        "ISOSpeed", "ISOSpeed_str",
        "av_gray",
        "temperature", "humidity",
        "sky_KW_J", "global_KW_J", "atmo_KW_J", "sun_zenit",
        "x_coord", "y_coord",
        "av_gray_y", "temperature_y", "humidity_y", "sky_KW_J_y", "global_KW_J_y", "atmo_KW_J_y", "sun_zenit_y"
        ]


def make_regex_YMDHm_word():
    # URL that generated this code: http://txt2re.com/
    # regex matching: >'2013_09_17_1937_IMG_9930.JPG'<
    re1 = '((?:(?:[1]{1}\\d{1}\\d{1}\\d{1})|(?:[2]{1}\\d{3})))(?![\\d])'  # Year 1
    re2 = '(_)'  # Any Single Character 1
    re3 = '(\\d)'  # Any Single Digit 1
    re4 = '(\\d)'  # Any Single Digit 2
    re5 = '(_)'  # Any Single Character 2
    re6 = '(\\d)'  # Any Single Digit 3
    re7 = '(\\d)'  # Any Single Digit 4
    re8 = '(_)'  # Any Single Character 3
    re9 = '(\\d)'  # Any Single Digit 5
    re10 = '(\\d)'  # Any Single Digit 6
    re11 = '(\\d)'  # Any Single Digit 7
    re12 = '(\\d)'  # Any Single Digit 8
    re13 = '(_)'  # Any Single Character 4
    re14 = '((?:[a-z][a-z]+))'  # Word 1
    re15 = '.*?'  # Non-greedy match on filler
    re16 = '(\\.)'  # Any Single Character 5
    re17 = '((?:[a-z][a-z]+))'  # Word 2

    rgx = re.compile(
        re1 + re2 + re3 + re4 + re5 + re6 + re7 + re8 + re9 + re10 + re11 + re12 + re13 + re14 + re15 + re16 + re17,
        re.IGNORECASE | re.DOTALL)
    return rgx


def make_regex_YMDHm_pict():
    # URL that generated this code:
    # http://txt2re.com/index-python.php3?s=2016_04_29_01_52_picts
    # txt = '2016_04_29_01_52_picts.csv'

    re1 = '((?:(?:[1]{1}\\d{1}\\d{1}\\d{1})|(?:[2]{1}\\d{3})))(?![\\d])'  # Year 1
    re2 = '(_)'  # Any Single Character 1
    re3 = '((?:(?:[0-2]?\\d{1})|(?:[3][01]{1})))(?![\\d])'  # Day 1
    re4 = '(_)'  # Any Single Character 2
    re5 = '((?:(?:[0-2]?\\d{1})|(?:[3][01]{1})))(?![\\d])'  # Day 2
    re6 = '(_)'  # Any Single Character 3
    re7 = '((?:(?:[0-2]?\\d{1})|(?:[3][01]{1})))(?![\\d])'  # Day 3
    re8 = '(_)'  # Any Single Character 4
    re9 = '(\\d)'  # Any Single Digit 1
    re10 = '(\\d)'  # Any Single Digit 2
    re11 = '(_)'  # Any Single Character 5
    re12 = '(picts)'  # Word 1
    re13 = '(\\.)'  # Any Single Character 6
    re14 = '(csv)'  # Word 2

    rgx = re.compile(re1 + re2 + re3 + re4 + re5 + re6 + re7 + re8 + re9 + re10 + re11 + re12 + re13 + re14,
                    re.IGNORECASE | re.DOTALL)
    # m = rg.search(txt)    # m = rg.search(txt)
    return rgx

def print_valid_picts_in_list(list_of_pict=list_of_pict):
    list_of_pict.sort(key = attrgetter('datum'))
    cnt_valid_picts = 0
    for pict in list_of_pict:
        # pprint.pprint(pict)
        if pict.Model != 'ToDo':
            cnt_valid_picts += 1
            out_str = '{:4d}'.format(cnt_valid_picts), pict
        else:
            out_str = 'Model = rh: ', pict

    if not quiet:
        print out_str
    return cnt_valid_picts

def print_all_picts_in_list():
    list_of_pict.sort(key = attrgetter('datum'))
    for pict in list_of_pict:
        pprint.pprint(pict)

def print_todo_picts_in_list():
    list_of_pict.sort(key = attrgetter('datum'))
    print 'Images to synthesize:' ,
    cnt_picts = 0
    for pict in list_of_pict:
        if pict.Model == 'ToDo':
            cnt_picts += 1
            if cnt_picts == 1:
                print
            print '{:4d}'.format(cnt_picts) + ': ', pict
    if cnt_picts == 0:
        print cnt_picts
    return cnt_picts

def initialize_list_of_picts():
    # >list_of_pict< is global
    global cnt_days
    start   = datetime.datetime.strptime(date_start, '%Y_%m_%d')
    end     = datetime.datetime.strptime(date_end, '%Y_%m_%d')
    step    = datetime.timedelta(days=1)
    cnt_days= 0
    act_day = start
    while act_day <= end:
        act_day_str = act_day.date().strftime('%Y_%m_%d')  # Formatieren
        pict = PictClass(act_day_str)
        pict.cnt = cnt_days
        list_of_pict.append(pict)
        act_day  += step
        cnt_days +=  1

def make_list_of_picts_via_EXIF():
    # >list_of_pict< is global
    stop_tag = 'UNDEF'
    reg_hhmm  = re.compile(r"^\d{4}_[A-Za-z]")
    reg_YMDHm = make_regex_YMDHm_word()#
    # reg_YYYY_MM_DD_hhmm = re.compile(r"^\d{4}_[A-Za-z]")  #
    cnt_jpg_picts = 0
    root, dirs, files = os.walk(root_dir).next()  # only first level
    for f_name in files:  # only files, not subdirs
        Y_M_D_prefix = 'Y_M_D_prefix_?'
        path_f_name = os.path.join(root, f_name)
        ext = os.path.splitext(path_f_name)[-1].lower()  # get fn-extension
        if ext == ".jpg": # jpg's
            cnt_jpg_picts += 1
            new_f_name = '*'
            new_path_f_name = '*'
            Make = 'Manufacturer_?'
            Model = 'Model_?'
            Y_M_D_prefix  = 'Y_M_D_prefix_??'
            date_time_str = '0'
            FNumber = '0'
            ExposureTime = '0'
            ISOSpeed = '0'

            try:
                im_file = open(path_f_name, 'rb')
            except:
                print "'%s' is unreadable\n" % path_f_name
                continue
            # now get EXif tags:
            data = exifread.process_file(im_file, details=False)
            im_file.close()

            for key in data.keys():
                if key.find('Item') >= 0:  # dummy for pattern
                    Item = data[key].printable  # dummy for pattern

                if key.find('Make') >= 0:
                    Make = data[key].printable  # Manufacturer
                    # print 'Make =', Make

                if key.find('Model') >= 0:
                    Model = data[key].printable
                    if 'G1 X' in Model:
                        Model = 'G1 X'
                    if 'G15' in Model:
                        Model = 'G15 '

                if key.find('FNumber') >= 0:
                    FNumber_str = data[key].printable
                    # print 'FNumber =', FNumber_str
                    pos_slash = FNumber_str.find('/')
                    if pos_slash > 0:
                        counter = FNumber_str[:pos_slash]
                        denominator = FNumber_str[pos_slash + 1:]
                        FNumber = str(float(counter) / float(denominator))
                    else:
                        FNumber = str(float(FNumber_str))
                        # print 'FNumber =', FNumber

                if key.find('ExposureTime') >= 0:
                    ExposureTime = data[key].printable
                    # print 'ExposureTime =', ExposureTime,
                    pos_slash = ExposureTime.find('/')
                    if pos_slash > 0:
                        z = ExposureTime[:pos_slash]
                        n = ExposureTime[pos_slash + 1:]
                        ExposureTime_float = float(z) / float(n)
                    # print '= ', ExposureTime_float

                if key.find('ISOSpeed') >= 0:
                    ISOSpeed = data[key].printable
                    # print 'ISOSpeed =', ISOSpeed

                if key.find('DateTimeOriginal') >= 0:
                    date_time_str  = data[key].printable
                    hhmm_prefix    = date_time_str[11:13] + date_time_str[14:16]
                    hhmm_prefix    = hhmm_prefix.replace(' ', '0', -1)

                    Y_M_D_prefix   = date_time_str[0:4] + '_' + date_time_str[5:7] + '_' + date_time_str[8:10]
                    YMDHm_prefix   = Y_M_D_prefix + '_' + hhmm_prefix
                    if not quiet: print Y_M_D_prefix, YMDHm_prefix
                    if re.match(reg_hhmm, f_name):  # re.match == regex am Stringanfang?
                        new_f_name = YMDHm_prefix + '_' + f_name[5:]
                    elif reg_YMDHm.search(f_name):
                        new_f_name = YMDHm_prefix + '_' + f_name[16:]
                    else:
                        new_f_name = YMDHm_prefix + '_' + f_name

            # find pict in list_of_pict with pict.datum == Y_M_D_prefix
            new_path_f_name = os.path.join(root, new_f_name)
            pict = next((x for x in list_of_pict if x.datum == Y_M_D_prefix), None)
            if not pict:       # for this
                # print '! Y_M_D_prefix = >', Y_M_D_prefix,  '< No pict found!'
                pass
            elif pict.date :
                pass
                # print '!> f_name = >', f_name, '< Y_M_D_prefix = >', Y_M_D_prefix, '< and >', pict.date, '< exists .'
            else:
                # print '!> f_name = >', f_name, '< Y_M_D_prefix = >', Y_M_D_prefix, '< and >', pict.date, '< exists .'
                pict.date        = Y_M_D_prefix
                pict.Make        = Make
                pict.Model       = Model
                pict.fn          = new_f_name
                pict.fn_old      = f_name
                pict.path_fn     = new_path_f_name   # fn incl path
                pict.FNumber_str = FNumber_str
                pict.FNumber     = FNumber
                pict.ExpoTime_str= ExposureTime
                pict.ExpoTime    = ExposureTime_float # ExposureTime
                pict.ISOSpeed    = ISOSpeed
                pict.ISOSpeed_str= ISOSpeed
                pict.av_gray     = -999.0

    cnt_valid_picts = 0
    for pict in list_of_pict:
        if pict.Model != 'ToDo':  # == missing image == to be synthesized
            cnt_valid_picts += 1
    return cnt_jpg_picts, cnt_valid_picts

def make_result_path_fn (dir, fn):
    return os.path.join(root_dir,dir, fn)

def act_date_time_str():
    now = datetime.datetime.now()
    # dt_str = now.year + now.month + now.day + now.hour + now.minute
    return now.strftime("%Y_%m_%d_%H_%M_")
    # return dt_str

def picts_csv_write(list_of_pict):
    # >PictClass< erbt von >object< => >pict.__dict__< ist ein dictionary und kann mit >csv.DictWriter< serialisiert werden.
    # http://stackoverflow.com/questions/61517/python-dictionary-from-an-objects-fields
    # http://stackoverflow.com/questions/3086973/how-do-i-convert-this-list-of-dictionaries-to-a-csv-file-python
    fn = make_result_path_fn('results', act_date_time_str() + 'picts.csv')   # fn von csv file
    list_of_pict.sort(key = attrgetter('datum'))
    pict = list_of_pict[0]                            # erstes Element von >list_of_pict<
    fieldnames = pict.fieldnames                      # >fieldnames< from definition of PictClass

    for pict in list_of_pict:                     # changing data elements of picts after reading
        for key in pict.__dict__.keys():          # there may be datalements that not exist in fieldnames
            if key not in fieldnames:             # delete (== pop) any key in pict.__dict__, that is not in fieldnames
                pict.__dict__.pop(key, None)      # remember that >pict.__dict__< turns pict into dictionary!
        #'glb_y_coord', 'sun_y_coord', 'hum_y_coord', 'sky_y_coord', 'tmp_y_coord', 'atm_y_coord'

    with open(fn, 'wb') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames)
        writer.writeheader()                          # Header = >fieldnames<
        for pict in list_of_pict:
            # print pict.__dict__
            writer.writerow(pict.__dict__)            # write values of dictionary: >pict.__dict__<. dictionary!!
    # pprint.pprint(fieldnames)

def picts_csv_read():
    # (SilentGhost' answer is helpfull) but here we use _existing_ class -> simply adapt >PictClass.__init__<
    # http://stackoverflow.com/questions/1639174/creating-class-instance-properties-from-a-dictionary-in-python
    #
    # there are a lot of result files >YYYY_MM_DD_mm_result.csv< in the result dir => find the most recent one.
    reg_YMDHm_pict = make_regex_YMDHm_pict()#
    # os.path.join(root_dir, dir, fn)
    results_dir = os.path.join(root_dir, 'results', '')
    root, dirs, files = os.walk(results_dir).next()  # only first level
    result_files = []
    for f_name in files:  # only files, not subdirs
        # print f_name,
        if re.match(reg_YMDHm_pict, f_name):
            result_files.append(f_name)
            # print 'found result file: ', f_name
        else:
            pass
            # print

    fn = max(result_files)                             # most recent result file.
    result_fn = os.path.join(root_dir, 'results', fn)
    print '\n', 'Reading data from: \n>', result_fn
    #
    new_list_of_pict = []
    with open(result_fn, 'r') as csv_file:
        reader = csv.DictReader(csv_file)
        for pict_dict in reader:
            if not quiet:
                print pict_dict          # is a dict
            pict = PictClass(pict_dict)
            new_list_of_pict.append(pict)
    print 'successfull.'
    return new_list_of_pict

def make_rename_batch_file():
    list_of_pict.sort(key = attrgetter('datum'))
    cnt_picts = 0
    for pict in list_of_pict:
        if (pict.Model != 'ToDo') and (pict.fn_old != pict.fn):
            cnt_picts += 1
            batch_str = 'mv %s %s ' % (pict.fn_old , pict.fn)
            batch_file.write(batch_str + '\n')
    return cnt_picts


def adjust_EXIF_tags(pict):
    # https://github.com/hMatoba/Piexif
    # http://piexif-demo.appspot.com/demo
    # https://www.smallsurething.com/how-to-remove-exif-data-from-jpeg-images-in-python/
    print 'synthesized: ', pict.path_fn
    exif_dict = piexif.load(pict.path_fn)  # EXIF data as dictionary ...     (can not be written in file)
    exif_bytes = piexif.dump(exif_dict)    # transformed in byte - data. ... (can     be written in file)
    # pprint.pprint (exif_dict)
    # for ifd_name in exif_dict:
    #     # print ("\n{0} IFD:".format(ifd_name))
    #     if hasattr(exif_dict[ifd_name], "__iter__"):
    #         for key in exif_dict[ifd_name]:
    #             try:
    #                 # print (key, exif_dict[ifd_name][key][:10])
    #             except:
    #                 # print ('?')

    for ifd_name in exif_dict:
        if hasattr(exif_dict[ifd_name], "__iter__"):
            for key in exif_dict[ifd_name]:
                exif_dict[ifd_name] = {}

    # exif_dict['0th'][271] = 'synthesized'  # == Make
    # adjust Model tag:
    exif_dict['0th'][272] = 'synthesized'    # == Model ??
    # pprint.pprint(exif_dict)
    # adjust dates:
    dt = pict.datum
    date_str = dt[0:4] + ':' + dt[5:7]+ ':' + dt[8:10] + ' 09:00:00'
    # date_str = "2013:04:07 09:00:00"
    exif_dict['0th'][306]    = date_str
    # date_str = "2013:04:07 09:01:00"
    exif_dict['Exif'][36867] = date_str       # == DateTimeOriginal == Kameradatum
    # date_str = "2013:04:07 09:02:00"
    exif_dict['Exif'][36868] = date_str
    # convert format to bytes
    exif_bytes = piexif.dump(exif_dict)  # transforme EXIF-dict in byte-data. ... (can     be written in file)
    # save file with changed EXIF tag:
    piexif.insert(exif_bytes, pict.path_fn)
    if not quiet:
        print 'adjust EXIF Tag "Model" in: ' + pict.path_fn + '< to >synthesized< ok'

def test_EXIF_Tag(pict):
    # path_root = "D:\Data_Work\Other_Data\_Morgen_Himmel\"
    # path_sub_pics = "_Morgen_Himmel_alle_001"
    # l_path = "D:\Data_Work\Other_Data\_Morgen_Himmel\_Morgen_Himmel_alle_001"
    l_fn   = "2013_04_07_1222_IMG_2553_01.JPG"
    pict.path_fn = os.path.join(path_root, path_sub_pics, l_fn)
    print 'test_EXIF_Tag: ', pict.path_fn
    exif_dict = piexif.load(pict.path_fn)  # EXIF data as dictionary ...     (can not be written in file)
    exif_bytes = piexif.dump(exif_dict)    # transformed in byte - data. ... (can     be written in file)
    pprint.pprint (exif_dict)
    # for ifd_name in exif_dict:
    #     # print ("\n{0} IFD:".format(ifd_name))
    #     if hasattr(exif_dict[ifd_name], "__iter__"):
    #         for key in exif_dict[ifd_name]:
    #             try:
    #                 # print (key, exif_dict[ifd_name][key][:10])
    #             except:
    #                 # print ('?')

    for ifd_name in exif_dict:
        if hasattr(exif_dict[ifd_name], "__iter__"):
            for key in exif_dict[ifd_name]:
                exif_dict[ifd_name] = {}

    # exif_dict['0th'][271] = 'synthesized'  # == Make
    exif_dict['0th'][272]  = 'synthesized'   # == Model
    dt = pict.datum
    date_str = dt[0:4] + ':' + dt[5:7]+ ':' + dt[8:10] + ' 09:00:00'
    date_str = "2013:04:07 09:00:00"
    exif_dict['0th'][306]    = date_str
    date_str = "2013:04:07 09:01:00"
    exif_dict['Exif'][36867] = date_str      # == DateTimeOriginal == Kameradatum
    date_str = "2013:04:07 09:02:00"
    exif_dict['Exif'][36868] = date_str
    print date_str

    # pprint.pprint(exif_dict)
    exif_bytes = piexif.dump(exif_dict)  # transforme EXIF-dict in byte-data. ... (can     be written in file)
    # save file with changed EXIF tag:
    piexif.insert(exif_bytes, pict.path_fn)
    print 'test_EXIF_tag "Model" in: ' + pict.path_fn + '< to >synthesized< ok'



def temporary_corr_EXIF_of_synthesized_picts(list_of_pict=list_of_pict):
    # http://tilloy.net/dev/pyexiv2/
    # http: // tilloy.net / dev / pyexiv2 / tutorial.html
    for pict in list_of_pict:
        if pict.Model == 'synthesized': # find synthesized images
            # adjust_EXIF_tags(pict)
            pass
            # print 'synthesized: ', pict

    # adjust_EXIF_tags(pict = None)
    # pict = list_of_pict[0]
    # write_EXIF_explore()
    pass

def calc_model_type_picts():
    # calc's number of images per model
    dict_model_cnt = {}   # {model:cnt}
    list_of_pict.sort(key=attrgetter('Model', 'datum')) # sort list_of_pict

    for pict in list_of_pict:
        if pict.Model not in dict_model_cnt.keys():
            dict_model_cnt[pict.Model] = 1
        else:
            dict_model_cnt[pict.Model] = dict_model_cnt[pict.Model] + 1
    list_model_cnt = [] # of model_cnt  <> convert dict to list (better to sort)
    for model, cnt in sorted(dict_model_cnt.iteritems()):
        temp = [model, cnt]
        list_model_cnt.append(temp)

    list_model_cnt.sort(key=lambda x: x[0])

    print
    for model, cnt in list_model_cnt:
        print model + ':', cnt

    return list_model_cnt

def synthesize_image_and_save_it(pict_new, pict_1, pict_2, pict_3):
    im = Image.open(os.path.join(root_dir, pict_1.fn))
    red, g, b = im.split()
    im.close()
    im = Image.open(os.path.join(root_dir, pict_2.fn))
    r, green, b = im.split()
    im.close()
    im = Image.open(os.path.join(root_dir, pict_3.fn))
    r, g, blue = im.split()
    im.close()

    # img = Image.merge("RGB", (red, green, blue))
    attenuated_red = red.point(lambda i: i * 0.85)      # attenuate red channel
    img = Image.merge("RGB", (attenuated_red, green, blue))
    img.save((os.path.join(root_dir, synth_image_dir, pict_new.fn)))

def calc_and_store_FN_ExposureTime_ISOSpeed(pict_new, pict_1, pict_2, pict_3):
    # used lists are global. values are strings or corresponding floats

    global List_FNumbers
    global List_ExpoTimes
    global List_ISOSpeeds

    global List_FNumbers_float
    global List_ExpoTimes_float
    global List_ISOSpeeds_float

    # calc average (FNumber, Expotime, ISOSpeed) from the 3 source images.
    average_FNumber   = (float(pict_1.FNumber) + float(pict_2.FNumber) + float(pict_3.FNumber)) / 3
    average_ExpoTime  = (float(pict_1.ExpoTime) + float(pict_2.ExpoTime) + float(pict_3.ExpoTime)) / 3
    average_ISOSpeed  = (float(pict_1.ISOSpeed) + float(pict_2.ISOSpeed) + float(pict_3.ISOSpeed)) / 3

    # Look for the nearest norm-value by calculating deltas from corresponding list of norm-values
    # Use index to extract nearest value as fraction (as string)
    # val, idx = min((val, idx) for (idx, val) in enumerate(my_list))
    list_delta_FNumber = list(abs(float(x - average_FNumber)) for x in List_FNumbers_float)
    val, idx = min((val, idx) for (idx, val) in enumerate(list_delta_FNumber))
    # print 'delta: ', val, 'idx: ', idx, average_FNumber, List_FNumbers_float[idx], List_FNumbers[idx]
    pict_new.FNumber     = List_FNumbers_float[idx]
    pict_new.FNumber_str = List_FNumbers[idx]

    list_delta_ExpoTime = list(abs(float(x - average_ExpoTime)) for x in List_ExpoTimes_float)
    val, idx = min((val, idx) for (idx, val) in enumerate(list_delta_ExpoTime))
    pict_new.ExpoTime     = List_ExpoTimes_float[idx]
    pict_new.ExpoTime_str = List_ExpoTimes[idx]

    list_delta_ISOSpeed = list(abs(float(x - average_ISOSpeed)) for x in List_ISOSpeeds_float)
    val, idx = min((val, idx) for (idx, val) in enumerate(list_delta_ISOSpeed))
    pict_new.ISOSpeed     = List_ISOSpeeds_float[idx]
    pict_new.ISOSpeed_str = List_ISOSpeeds[idx]

def make_new_images_logstr (cnt, new_pict, pict_s):
    log_str = str(cnt) + ' ; ' + new_pict.fn + ' ; '
    log_str += pict_s[0].Model + ' ; ' + pict_s[0].fn + ' ; '
    log_str += pict_s[1].Model + ' ; ' + pict_s[1].fn + ' ; '
    log_str += pict_s[2].Model + ' ; ' + pict_s[2].fn + ' ; '
    log_str += '\n'
    return log_str

def list_synthesized_images():
    for pict in list_of_pict:
        if pict.Model == 'synthesized': # find synthesized images
            print pict

def synthesize_missing_picts():
    # following _global_ lists are used in >def calc_and_store_FN_ExposureTime_ISOSpeed<
    #   to calc FN_ExposureTime_ISOSpeed values
    global List_FNumbers
    global List_ExpoTimes
    global List_ISOSpeeds
    List_FNumbers = ["1.4", "1.8", "2", "2.2", "2.4", "2.8", "3.2", "3.5", "4", "4.5", "5", "5.6", "6.3", "6.5", "7.1",
                    "8", "9.5", "10", "11", "13", "16", "19", "22"]
    List_ExpoTimes = ["1/1000", "1/500", "1/250", "1/125", "1/60", "1/30", "1/15", "1/8", "1/4", "1/2", "1"]
    List_ISOSpeeds = ["25", "50", "64", "100", "200", "400", "800", "1600", "3200", "6400", "12800", "25600", "51200",
                     "102400", "204800"]

    global List_FNumbers_float
    global List_ExpoTimes_float
    global List_ISOSpeeds_float
    List_FNumbers_float = list(float(Fraction(x)) for x in List_FNumbers)
    List_ExpoTimes_float = list(float(Fraction(x)) for x in List_ExpoTimes)
    List_ISOSpeeds_float = list(float(Fraction(x)) for x in List_ISOSpeeds)

    # synth images:
    # a) combine r,g,b channels from 3 different images of _same_ camera model (to conserve dimensions, geometry etc)
    # b) relation of camera model of new images reflects relation of camera models of existing images
    # c) o calc FN_ExposureTime_ISOSpeed values by calling function
    # d) log all
    #
    list_model_cnt = calc_model_type_picts()    # list: how many img's from which camera model ?
    iter_list_model_cnt = iter(list_model_cnt)  # convert list to iterator
    model, cnt_g1X = iter_list_model_cnt.next() # idx in list_of_pict of last G1X pict:  first  model (G1 X)
    model, cnt_g15 = iter_list_model_cnt.next() # idx in list_of_pict of last G1X pict:  second model (G15)
    # cnt_synthd_images of all existing images == (cnt_g1X + cnt_g15) == 100%  = 0 .. 1.0
    # cut == percentage of G1X - images; (1 - cut) == percentage of G15 - images
    cut =  float(cnt_g1X) / (float(cnt_g15) + float(cnt_g1X))  # relation cnt_G1X to cnt_G15
    list_of_pict.sort(key=attrgetter('Model', 'datum'))        # sort in place

    log_fn = 'new_images_test.log'                                      # log filename
    log_f  = open(os.path.join(root_dir, synth_image_dir, log_fn), 'w') # log file in sub dir

    cnt_synthd_images = 0
    for pict in list_of_pict:
        if pict.Model == 'ToDo':          # find fn of next image to synthesize
            print "\r", 'synthesizing new image # ', cnt_synthd_images,
            pict_to_synth = pict
            if random.random() < cut:   # 1 .. cnt_g1X - 1   == range with G1 X images
                low = 1
                high = cnt_g1X - 1
            else:                       # cnt_g1X .. cnt_g15 == range with G15 images
                low  = cnt_g1X
                high = cnt_g1X + cnt_g15 - 1

            pict_s = []
            for idx in range(0,3):  # 0,1,2 i.e. find 3 images in the same range (with same model) as 'pict_synth'.
                l_pict = list_of_pict[int(round(random.uniform(low, high)))]  # low, high == range of G1X or G15
                pict_s.append(l_pict)

            # print (log_str)
            # synthesize image, save it:
            synthesize_image_and_save_it(pict_to_synth, pict_s[0], pict_s[1], pict_s[2])
            # adjust >path_fn< in >pict< object
            pict_to_synth.path_fn = (os.path.join(root_dir, synth_image_dir, pict.fn))
            # adjust EXIF Make tag in jpeg-file (!) to :'synthesized'
            adjust_EXIF_tags(pict_to_synth)
            # inc counter
            cnt_synthd_images += 1
            #
            # store names of source images in >pict< object:
            pict_to_synth.sources = pict_s[0].fn + ', ' + pict_s[1].fn + ', ' + pict_s[2].fn
            # calc virtual FNumber, ExposureTime and ISOSpeed of synthesized image
            calc_and_store_FN_ExposureTime_ISOSpeed (pict_to_synth, pict_s[0], pict_s[1], pict_s[2])
            # mark it as synthesized image in >pict< object
            pict_to_synth.Model   = 'synthesized'
            # compose log_str and write it to file
            log_str = make_new_images_logstr(cnt_synthd_images, pict_to_synth, pict_s)
            log_f.write(log_str)

    log_f.close()
    # show what you've done
    if cnt_synthd_images > 0:
        list_synthesized_images()
        return cnt_synthd_images
    else:
        print "No new images to synthesize."
        return cnt_synthd_images


def calc_average_graylevel():
    # print '>>>>>>>> calc_average_graylevel():'
    list_of_pict.sort(key = attrgetter('Model', 'datum'))
    cnt = 0
    for pict in list_of_pict:
        cnt += 1
        print "\r  ", cnt, ': image # ', pict.fn, ' gray level = ',
        image = Image.open(pict.path_fn).convert('L')
        im_np_array  = np.array(image)
        pict.av_gray = "{:.2f}".format(np.average(im_np_array))  # "{:.9f}".format(numvar)
        print pict.av_gray

def find_max_width_max_height_of_pict():
    cnt = 0
    list_width, list_height = [], []
    for pict in list_of_pict:
        # if pict.Model !=
        cnt += 1
        # print "\r  ", cnt, ': image # ', pict.fn,
        with Image.open(pict.path_fn) as img:
            width, height = img.size
            list_width.append (width)
            list_height.append(height)

    max_width, max_height = max(list_width), max(list_height)
    min_width, min_height = max(list_width), max(list_height)

    print '\n{:4d}'.format(cnt), 'images:', 'max_width = ', max_width, 'max_height = ', max_height
    print '            ', 'min_width = ', min_width, 'min_height = ', min_height
    return max_width, max_height

def connect_picts_with_DWD_data():
    # connect pict to temperature, humidity, cloudiness, ....
    # -----------------------------------------------------------------------------------------------
    # temperature, humidity:
    DWD_data_file_fn = "Data_Temperature\produkt_temp_Terminwerte_19970701_20151231_03379_reduced.txt"
    DWD_data_path_fn = os.path.join(path_root, path_sub_DWD, DWD_data_file_fn)
    # print DWD_data_path_fn
    data_list  = []   # == whole line of input file
    time_list  = []   # == timestamp  of input file
    val_1_list = []   # == data_value #1 of input file, i.e. temperature, humidity or cloudiness and so on
    val_2_list = []   # == data_value #2 of input file, i.e. temperature, humidity or cloudiness and so on
    # STATIONS_ID; MESS_DATUM; QUALITAETS_NIVEAU; STRUKTUR_VERSION; LUFTTEMPERATUR;REL_FEUCHTE;eor
    with open(DWD_data_path_fn) as data_f:
        for line in data_f:
            data_list.append (line)                       # whole line of data-file
            time_list.append (long(line.split(';')[1]))   # timestamps  == second row
            val_1_list.append(float(line.split(';')[4]))  # temperature at this timestamps
            val_2_list.append(float(line.split(';')[5]))  # temperature at this timestamps

    list_of_pict.sort(key = attrgetter('datum'))
    for pict in list_of_pict:
        pict_time_long = long (pict.fn[0:4] + pict.fn[5:7] + pict.fn[8:10] + pict.fn[11:13])
        # print "pict.datum =", pict.datum, " pict_time =", pict_time_long,
        list_delta_tempTime = list(abs(x - pict_time_long) for x in time_list)
        delta_t, idx = min((val, idx) for (idx, val) in enumerate(list_delta_tempTime))
        if not quiet:
            print "time_list[idx] =", time_list[idx], "delta_t =", delta_t, # "idx =", idx,
            print "temperature =", val_1_list[idx],
            print "humidity =",    val_2_list[idx]
        pict.temperature = val_1_list[idx]
        pict.humidity = val_2_list[idx]

    # -----------------------------------------------------------------------------------------------
    # DIFFUS_HIMMEL_KW_J, GLOBAL_KW_J, ATMOSPHAERE_LW_J:
    DWD_data_file_fn = "Data_Solar\produkt_strahlung_Stundenwerte_19610101_20160331_05404_reduced.txt"
    DWD_data_path_fn = os.path.join(path_root, path_sub_DWD, DWD_data_file_fn)
    # print DWD_data_path_fn
    data_list = []  # == whole line of input file
    time_list = []  # == timestamp  of input file
    val_1_list = [] # == data_value #1 of input file, DIFFUS_HIMMEL_KW_J
    val_2_list = [] # == data_value #2 of input file, GLOBAL_KW_J
    val_3_list = [] # == data_value #2 of input file, ATMOSPHAERE_LW_J
    val_4_list = [] # == data_value #2 of input file, SONNENZENIT
    # STATIONS_ID; MESS_DATUM; QUALITAETS_NIVEAU; SONNENSCHEINDAUER;DIFFUS_HIMMEL_KW_J;GLOBAL_KW_J;ATMOSPHAERE_LW_J;SONNENZENIT;MESS_DATUM_WOZ;eor
    with open(DWD_data_path_fn) as data_f:
        for line in data_f:
            data_list.append(line)                        # whole line of data-file
            time_list.append(long(line.split(';')[1][:10]))    # timestamps  == second row
            val_1_list.append(float(line.split(';')[3]))  # DIFFUS_HIMMEL_KW_J
            val_2_list.append(float(line.split(';')[4]))  # GLOBAL_KW_J
            val_3_list.append(float(line.split(';')[5]))  # ATMOSPHAERE_LW_J
            val_4_list.append(float(line.split(';')[6]))  # SONNENZENIT

    list_of_pict.sort(key=attrgetter('datum'))
    for pict in list_of_pict:
        pict_time_long = long(pict.fn[0:4] + pict.fn[5:7] + pict.fn[8:10] + pict.fn[11:13])
        # print "pict.datum =", pict.datum, " pict_time =", pict_time_long,
        list_delta_tempTime = list(abs(x - pict_time_long) for x in time_list)
        delta_t, idx = min((val, idx) for (idx, val) in enumerate(list_delta_tempTime))
        if not quiet:
            print "time_list[idx] =", time_list[idx], # "delta_t =", delta_t,  "idx =", idx,
            print "HIMMEL_KW_J =", val_1_list[idx],
            print "GLOBAL_KW_J =", val_2_list[idx],
            print "ATMOSPHAERE_LW_J =", val_3_list[idx],
            print "SONNENZENIT =", val_4_list[idx]

        pict.sky_KW_J    = val_1_list[idx]
        pict.global_KW_J = val_2_list[idx]
        pict.atmo_KW_J   = val_3_list[idx]
        pict.sun_zenit   = val_4_list[idx]

        if pict.global_KW_J == -999.0:
            pict.global_KW_J = ''
        if pict.sun_zenit == -999.0:
            pict.sun_zenit = ''


def reduce_image_resolution():
    global x_pict  # pixels on x-axis of single pict
    global y_pict  # pixels on y-axis of single pict

    list_of_pict.sort(key=attrgetter('datum'))
    for pict in list_of_pict:
        img = Image.open(pict.path_fn)
        fn  = make_result_path_fn('resized_3', pict.fn)
        print 'resizing: ', fn,
        img_resized = img.resize((x_pict, y_pict), Image.ANTIALIAS)
        img_resized.save(fn)
        print ' done.'


def plotting_01():
    # Pixelorientierte Graphik:
    # http://stackoverflow.com/questions/13714454/specifying-and-saving-a-figure-with-exact-size-in-pixels
    # Rand um Bild herum entfernen
    # http://stackoverflow.com/questions/8775622/exact-figure-size-in-matplotlib-with-title-axis-labels
    # Transparenter Hintergrund:
    # http://stackoverflow.com/questions/4581504/how-to-set-opacity-of-background-colour-of-graph-wit-matplotlib
    pass

def stitch_images():
    # http://stackoverflow.com/questions/10647311/how-do-you-merge-images-using-pil-pillow
    # https://www.youtube.com/watch?v=ZTjiDStstmc # image processing beyond PIL
    # https://www.youtube.com/watch?v=Wvvxazwi2IY # Image Processing in Python with Scikits-image
    #
    # http://stackoverflow.com/questions/18550127/virtual-file-processing-in-python
    #
    global res_image
    global res_curves
    global res_figures

    global x_pict   # pixels on x-axis of single pict
    global y_pict   # pixels on y-axis of single pict
    global border   # border

    x_max = x_cnt_pct # global
    y_max = y_cnt_pct # global
    print '\n'
    print "x_img_dim =" , x_img_dim,
    print "y_img_dim =" , y_img_dim,
    print "(x_img_dim * y_img_dim (MB)) =" , x_img_dim * y_img_dim // 1000000
    print "x_pict =" , x_pict,
    print "y_pict =" , y_pict,
    print "border =" , border
    print "x_max =" , x_max,
    print "y_max =" , y_max,
    print '\n'

    fn = make_result_path_fn('results', act_date_time_str() + 'img_result.jpg')   # fn von image file
    # fn = make_result_path_fn('results', act_date_time_str() + 'img_result.png')   # fn von image file
    print '\n', fn, '\n'

    res_image = Image.new('RGB', (x_img_dim, y_img_dim), (100, 100, 25, 0))

    # res_image.save(fn, optimize=True, quality=50)
    # return
    cnt = 0
    list_of_pict.sort(key=attrgetter('datum'))
    pict_iter = iter(list_of_pict)
    y_idx = border

    print 'cwd = ', os.getcwd()

    for y_cnt in range (0, y_max):
        y_idx = y_idx + border
        x_idx = border
        for x_cnt in range(0, x_max):
            x_idx = x_idx + border
            pict = pict_iter.next()

            # plot vals:
            fig = plt.figure()
            axplot = fig.add_axes([0.07, 0.25, 0.90, 0.70])
            axplot.plot(scipy.randn(100))
            numicons = 8
            for k in range(numicons):
                axicon = fig.add_axes([0.07 + 0.11 * k, 0.05, 0.1, 0.1])
                axicon.imshow(scipy.rand(4, 4), interpolation='nearest')
                axicon.set_xticks([])
                axicon.set_yticks([])
            fig.show()
            # fig.savefig('iconsbelow.png')

            # plot values:

            # img = plt.imread(pict.path_fn)
            # implot = plt.imshow(img)
            # # plt.scatter([10], [20])
            # # put a red dot, size 40, at 2 locations:
            # plt.scatter(x=[30, 40], y=[50, 60], c='r', s=40)
            # plt.show()
            # plt.savefig('tmp.jpg', bbox_inches='tight')
            # wie bisher:
            # img  = Image.open(pict.path_fn)
            img  = Image.open('tmp.jpg')


            print str(x_cnt) + ':' + str(y_cnt) + ' ' + str(x_idx) + ':' + str(y_idx) + ' | ' ,
            pict.x_coord = str(x_idx) # x_coord in result_image
            pict.y_coord = str(y_idx) # y_coord in result_image
            res_image.paste(img, (x_idx, y_idx))
            x_idx = x_idx + x_pict

        y_idx = y_idx + y_pict
        print
        cnt += 1
        if cnt > 1:
            break

    # http://stackoverflow.com/questions/5073386/how-do-you-directly-overlay-a-scatter-plot-on-top-of-a-jpg-image-in-matplotlib



    # res_image.show(fn)
    print '\n', fn, '\n'
    print '\n Dimensions x * y:', x_idx, '*', y_idx, '\n\n'
    res_image.save(fn, optimize=True, quality=50)
    # res_image.save(fn, optimize=True, quality=95)
    # print_all_picts_in_list():


def calc_measurement_coord():
    # task: in every single picture just show graphically for certain interesting parameters (temperature, humidity, av_gray ...)
    # the value as points. THe height is indicating the normalized values.
    # So: for every parameter
    #     find the range (i.e. min, max)
    #     calculate correspondig datapoint.
    # a little bit tricky:
    # we dynamically create dictionarys with
    #   keys corresponding to the fieldnames (i.e. : 'av_gray', 'temperature', 'humidity', ...)  and
    #   vals corresponding to lists containing the values of this field of all the pics (i.e. 'av_gray': [a1, a2, .. an]
    # We identify the corresponding min and max for every parameter; 
    #
    # Now we want to calculate the corresponding data point of every single specific value:
    # lowest val  == lower border of pictuere + something ; 
    # highest val == higher border of pictuere - something ;
    # Remember to scale according to the picture dimensions and the cale factor.
    #

    list_of_pict.sort(key=attrgetter('datum'))
    pict = list_of_pict[0]                            # erstes Element von >list_of_pict<
    # fieldnames = pict.fieldnames                      # >fieldnames< from definition of PictClass
    fieldnames = ['av_gray',   'temperature',   'humidity',   'sky_KW_J',   'global_KW_J',   'atmo_KW_J',   'sun_zenit']
               #  'av_gray_y', 'temperature_y', 'humidity_y', 'sky_KW_J_y', 'global_KW_J_y', 'atmo_KW_J_y', 'sun_zenit_y']
    # 'x_coord', 'y_coord',

    # initialize dicts:
    dict_values = {}
    dict_min = {}
    dict_max = {}

    # initialize lists in dicts (these lists are the vals of the dicts, i.e. key:[]):
    for fieldname in fieldnames:
        dict_values[fieldname] = []  # dict with k:v == fieldname:[pict[0].fieldname, pict[1].fieldname, ...]
        dict_min[fieldname]    = []  # dict with k:v == fieldname:[min (pict[0..n)].fieldname)]
        dict_max[fieldname]    = []  # dict with k:v == fieldname:[max (pict[0..n)].fieldname)]

    # for every element in dict_values, 'field_name':list, fill the list with pct.field_name[0 ... n]:
    for pict in list_of_pict:
        for fieldname in fieldnames:
            # dict_values[fieldname].append(float(getattr(pict, fieldname)))  # pict.fieldname
            strg = getattr(pict, fieldname)
            if strg:
                dict_values[fieldname].append(float(strg))  # pict.fieldname

    # for fieldname in fieldnames:
    #     # pprint.pprint (dict_values[fieldname])  # pict.fieldname
    #     # dict_values[fieldname].sort()  # pict.fieldname
    #     print fieldname, sorted(dict_values[fieldname])  # pict.fieldname

    # find (and store) min max in every list:
    print
    for fieldname in fieldnames:  # 
        if dict_values[fieldname]:
            dict_min[fieldname].append(min (dict_values[fieldname]))  # pict.fieldname min
            dict_max[fieldname].append(max (dict_values[fieldname]))  # pict.fieldname max
            print fieldname, dict_min[fieldname][0], dict_max[fieldname][0]

    # Now the data points and the scaling stuff:
    #
    x_edge_low,  y_edge_low  = x_pict // 10 , y_pict // 10
    x_edge_high, y_edge_high = x_pict // 10 , y_pict - y_pict // 10

    test_min_max = []

    for pict in list_of_pict:
        for fieldname in fieldnames:
            # if dict_values[fieldname]:
            if getattr(pict, fieldname):
                print pict.datum, fieldname,
                # dict_values[fieldname].append(float(getattr(pict, fieldname)))  # pict.fieldname
                val_min = float (dict_min[fieldname][0])
                val_max = float (dict_max[fieldname][0])
                val_pict= float (getattr(pict, fieldname))
                img_y   = int ((y_pict * (val_pict - val_min) * 0.8) // (val_max - val_min))
                print ':', getattr(pict, fieldname), dict_min[fieldname][0], dict_max[fieldname][0],
                print ':', val_min - val_min, val_pict - val_min, val_max - val_min, ':', img_y
                setattr(pict, fieldname + '_y', img_y)
                test_min_max.append(img_y)
        print
    # print min(test_min_max), max(test_min_max)


    #======================================================================

do_make_rename_file      = True
do_make_rename_file      = False

do_synthesize_new_images = True
do_synthesize_new_images = False

do_calc_average          = True
do_calc_average          = False

do_connect_with_DWD_data = True
do_connect_with_DWD_data = False

do_calc_measurement_coord= True
# do_calc_measurement_coord= False

do_stitch_images = True
# do_stitch_images = False

if __name__ == '__main__':
    # >list_of_pict< is global
    # global list_of_pict

    quiet, do_calc_average, do_make_rename_file = get_opts_args()

    initialize_list_of_picts()

    if do_make_rename_file:
        cnt_picts_to_rename = make_rename_batch_file()
        print "\n\n>" + batch_f_name + "< written. ", cnt_picts_to_rename, "files to rename\n"
        batch_file.close()

    list_of_pict = picts_csv_read()

    cnt_jpg_files, cnt_valid_files = make_list_of_picts_via_EXIF()  # *.jpg files in directory
    cnt_valid_picts                = print_valid_picts_in_list()    # picts in list
    cnt_missing_picts              = print_todo_picts_in_list()
    # print '\n', '{:4d}'.format(cnt_missing_picts), ' fehlen. '

    print "\n\n"
    '{:4d}'.format(cnt_valid_picts)
    print ">", '{:4d}'.format(cnt_days),           "days    in total"
    print ">", '{:4d}'.format(cnt_jpg_files),      "jpg     files in directory "
    print ">", '{:4d}'.format(cnt_valid_files),    "valid   files in directory "
    print ">", '{:4d}'.format(cnt_valid_picts),    "valid   picts in list "
    print ">", '{:4d}'.format(cnt_missing_picts),  "missing picts in list "

    # calc_model_type_picts()   # show number of picts for every camera model
    # picts_csv_write(list_of_pict)

    cnt_synthd_images = 0
    if do_synthesize_new_images:
        cnt_synthd_images = synthesize_missing_picts()
        cnt_valid_picts = print_valid_picts_in_list()  # picts in list
        print ">", '{:4d}'.format(cnt_valid_picts), " valid   picts in list "
        picts_csv_write(list_of_pict)
        list_of_pict = picts_csv_read()

    # test_EXIF_Tag(list_of_pict[0])

    if do_calc_average or cnt_synthd_images:   # if no image changed, no calculation
        calc_average_graylevel()
        picts_csv_write(list_of_pict)
        list_of_pict = picts_csv_read()

    # print_all_picts_in_list()
    # picts_show_class_members(list_of_pict)

    # temporary_corr_EXIF_of_synthesized_picts(list_of_pict)

    # max_w, max_h = find_max_width_max_height_of_pict() # => All picts are: x_pict_org * y_pict_org

    if do_connect_with_DWD_data:
        connect_picts_with_DWD_data()
        picts_csv_write(list_of_pict)
        list_of_pict = picts_csv_read()


    if do_calc_measurement_coord:  # if no image changed, no calculation
        calc_measurement_coord()
        # picts_csv_write(list_of_pict)
        # list_of_pict = picts_csv_read()

    # reduce_image_resolution()
    # 2016-05_04 images resized to 1/4 of original dimensions

    if do_stitch_images:
        stitch_images()
        picts_csv_write(list_of_pict)

    picts_csv_write(list_of_pict)

    print "\n> end"
