#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# rh: 2009-10_02
# rh: 2014-03_29   vs 0.2
# rh: 2016-04_09   vs 0.3
#
# Version um:
# 1. die Morgenphotos umzubenennen: YYYY_MM_DD_HH_mm_SS_IMGxxxx.jpg
# 2. Belichtungszeit, FNumber und ISOSpeed zu extrahieren
# 3. CSV File zu erstellen mit fn, Uhrzeit, ExpsTime, F und ISOSpeed
# 4. Fehlende Bilder ersetzen (406 = 2 * 7 * 29)
#
# Output:
# 1. neuen Filenamen samt Path 
# 2. (Batchfile)
#
# https://pypi.python.org/pypi/ExifRead
#
## TODO list of pictures:
## Für jedes Bild soll ein Objekt (iS eines -> data members) angelegt werden, das in einer Liste landet.
## Listen von Data member kann man auch gut sortieren:
##   http://stackoverflow.com/questions/403421/how-to-sort-a-list-of-objects-in-python-based-on-an-attribute-of-the-objects
## Dicts und Listen von DIcts kann man auch gut sortieren:
## https://wiki.python.org/moin/HowTo/Sorting  -> 'itemgetter' !!
##
## TODO dummy Bilder für die fehlenden Bilder erzeugen:
## Geht mit pil
## TODO mit pickle die Liste der pict sichern:

import datetime
import getopt
import os
import re
import sys
from operator import itemgetter, attrgetter, methodcaller

import exifread
# https://books.google.de/books?id=YRHSCgAAQBAJ&pg=PA96&lpg=PA96&dq=pil+average+grayscale&source=bl&ots=tsJ8nbYvua&sig=OHKPOAlTMV08S-p5jS-t_RacTS0&hl=de&sa=X&ved=0ahUKEwjrxo2I2JHMAhWEJhoKHY_rB0cQ6AEIRzAE#v=onepage&q=pil%20average%20grayscale&f=false
import numpy as np
from PIL import Image

do_calc_average    = True
do_calc_average    = False
do_make_batch_file = False
do_make_csv_file   = False
do_make_csv_file   = True

dict_of_pict = {}
list_of_pict = []

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
    msg += '  -d --dir=     directory.\n'
    msg += '  -q --quiet    quiet (default)\n'
    msg += '\n'
    print msg
    if exit_status:
        sys.exit(exit_status)

def get_opts_args():
    quiet = False
    root_dir = ''
    global do_calc_average
    global do_make_csv_file
    global csv_file
    global csv_f_name
    global do_make_batch_file
    global batch_file
    global batch_f_name

    try:
        #  >:< option requires argument
        opts, args = getopt.getopt(sys.argv[1:], "acbd:hvq", ["--avrge", "csv", "batch", "dir=", "verbose", "quiet"])
    except getopt.GetoptError:
        usage(2)
    if not args:
        usage(0)

    for o, a in opts:
        if o in ("-a", "--avrge"):
            do_calc_average = True
        if o in ("-b", "--batch"):
            do_make_batch_file = True
        if o in ("-c", "--csv"):
            do_make_csv_file = True
        if o in ("-d", "--dir"):
            root_dir = a
        if o in ("-w", "--write_files"):
            do_write_files = True
        if o in ("-h", "--help"):
            usage(0)

    if not root_dir:
        root_dir = '.'
        root_dir = 'D:\Data_Work\Photos\_Extra\Morgen_Himmel\Morgen_Himmel_alle'
        root_dir = 'D:\Data_Work\Photos\_Extra\Morgen_Himmel\Morgen_Himmel_alle_001'

    if not quiet:
        print 'root_dir: >' + root_dir + '<'
    if not os.path.isdir(root_dir):
        print 'Directory >' + root_dir + '< does not exist.'
        sys.exit(2)

    if do_make_batch_file:
        try:
            batch_f_name = 'rename_photos.bat'
            batch_f_name = os.path.join(root_dir, batch_f_name)
            batch_file = open(batch_f_name, 'wb')
        except:
            print "'%s' is unwritable\n" % batch_f_name
            sys.exit(2)

    if do_make_csv_file:
        try:
            csv_f_name = 'photos_values.csv'
            csv_f_name = os.path.join(root_dir, csv_f_name)
            csv_file = open(csv_f_name, 'wb')
        except:
            print "'%s' is unwritable\n" % csv_f_name
            sys.exit(2)

    return root_dir, quiet, do_calc_average, do_make_batch_file, do_make_csv_file


# http://www.tutorialspoint.com/python/python_classes_objects.htm
class PictClass():
    def __init__(self, datum):
        self.datum       = datum
        self.date        = ''
        self.Make        = 'rh'
        self.Model       = 'rh'
        self.date        = ''
        self.fn          = ''
        self.fn_old      = ''
        self.path_fn     = ''
        self.FNumber_str = ''
        self.FNumber     = ''
        self.ExpsTime    = ''
        self.ISOSpeed    = ''
        self.av_gray     = '99'

    def __repr__(self):
        return '"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s"' % ( \
        self.datum , \
        self.Make , \
        self.Model , \
        self.date , \
        self.fn , \
        self.fn_old , \
        self.path_fn , \
        self.FNumber_str , \
        self.FNumber , \
        self.ExpsTime , \
        self.ISOSpeed , \
        self.av_gray )

def print_list_of_pict():
    list_of_pict.sort(key = attrgetter('Model', 'datum'))
    cnt_files = 0
    for pict in list_of_pict:
        # pprint.pprint(pict)
        print(pict)
        cnt_files += 1
    return cnt_files

def print_list_of_missing_pict():
    cnt_files = 0
    for pict in list_of_pict:
        if pict.Make == 'rh':
            print(pict)
            cnt_files += 1
    return cnt_files

def initialize_list_of_pict():
    # >list_of_pict< and >dict_of_pict< are global
    global cnt_days
    date1   = '2013_04_07'
    date2   = '2014_08_16'
    start   = datetime.datetime.strptime(date1, '%Y_%m_%d')
    end     = datetime.datetime.strptime(date2, '%Y_%m_%d')
    step    = datetime.timedelta(days=1)
    cnt_days= 0
    act_day = start
    while act_day <= end:
        act_day_str = act_day.date().strftime('%Y_%m_%d')  # Formatieren
        pict = PictClass(act_day_str)
        list_of_pict.append(pict)
        dict_of_pict.update({act_day_str : pict})
        act_day  += step
        cnt_days +=  1

def make_list_of_pict():
    # >list_of_pict< and >dict_of_pict< are global
    stop_tag = 'UNDEF'
    reg_hhmm = re.compile(r"^\d{4}_[A-Za-z]")  #
    # reg_YYYY_MM_DD_hhmm = re.compile(r"^\d{4}_[A-Za-z]")  #
    cnt_jpg_files = 0
    root, dirs, files = os.walk(root_dir).next()  # only first level
    for f_name in files:  # only files
        path_f_name = os.path.join(root, f_name)
        ext = os.path.splitext(path_f_name)[-1].lower()
        if ext == ".jpg":
            cnt_jpg_files += 1
            print '\n', '{:4d}'.format(cnt_jpg_files), ': ', f_name

            new_f_name = '*'
            new_path_f_name = '*'

            Make = 'Manufacturer_?'
            Model = 'Model_?'
            date_time_str = '0'
            FNumber = '0'
            ExposureTime = '0'
            ISOSpeed = '0'

            try:
                im_file = open(path_f_name, 'rb')
            except:
                print "'%s' is unreadable\n" % path_f_name
                continue
            # get EXif tags:
            data = exifread.process_file(im_file, details=False)
            im_file.close()

            for key in data.keys():
                if key.find('Item') >= 0:  # dummy for pattern
                    Item = data[key].printable  # dummy for pattern

                if key.find('Make') >= 0:
                    Make = data[key].printable  # Manufacturer
                    print 'Make =', Make

                if key.find('Model') >= 0:
                    Model = data[key].printable
                    print 'Model =', Model

                if key.find('FNumber') >= 0:
                    FNumber_str = data[key].printable
                    print 'FNumber =', FNumber_str
                    pos_slash = FNumber_str.find('/')
                    if pos_slash > 0:
                        counter = FNumber_str[:pos_slash]
                        denominator = FNumber_str[pos_slash + 1:]
                        FNumber = str(float(counter) / float(denominator))
                        print 'FNumber =', FNumber

                if key.find('ExposureTime') >= 0:
                    ExposureTime = data[key].printable
                    print 'ExposureTime =', ExposureTime,
                    pos_slash = ExposureTime.find('/')
                    if pos_slash > 0:
                        z = ExposureTime[:pos_slash]
                        n = ExposureTime[pos_slash + 1:]
                        ExposureTime_float = float(z) / float(n)
                    print '= ', ExposureTime_float

                if key.find('ISOSpeed') >= 0:
                    ISOSpeed = data[key].printable
                    print 'ISOSpeed =', ISOSpeed

                if key.find('DateTimeOriginal') >= 0:
                    date_time_str = data[key].printable
                    hhmm_prefix = date_time_str[11:13] + date_time_str[14:16]
                    hhmm_prefix = hhmm_prefix.replace(' ', '0', -1)

                    Y_M_D_prefix = date_time_str[0:4] + '_' + date_time_str[5:7] + '_' + date_time_str[8:10]
                    YMDHm_prefix = Y_M_D_prefix + '_' + hhmm_prefix
                    if not quiet: print Y_M_D_prefix, YMDHm_prefix
                    if re.match(reg_hhmm, f_name):  # re.match == regex am Stringanfang?
                        new_f_name = YMDHm_prefix + '_' + f_name[5:]
                    else:
                        new_f_name = YMDHm_prefix + '_' + f_name

            # f_name = basename(path_f_name)

            pict = dict_of_pict[Y_M_D_prefix]
            # pict.datum    = datum
            pict.date     = Y_M_D_prefix
            pict.Make     = Make
            pict.Model    = Model
            pict.fn       = new_f_name
            pict.fn_old   = f_name
            # pict.path_fn = new_path_f_name
            pict.path_fn  = ''
            pict.FNumber  = FNumber
            pict.ExpsTime = ExposureTime_float
            pict.ISOSpeed = ISOSpeed
            pict.av_gray  = 99

def make_rename_batch_file():
    list_of_pict.sort(key = attrgetter('Model', 'datum'))
    for pict in list_of_pict:
        # new_path_f_name = os.path.join(root, pict.new_f_name)
        if pict.Make != 'rh':
            batch_str = 'mv %s %s ' % (pict.fn_old , pict.fn)
            batch_file.write(batch_str + '\n')

def make_csv_file():
    list_of_pict.sort(key = attrgetter('Model', 'datum'))
    cnt_jpg_files = 0
    sep = ' ; '
    for pict in list_of_pict:
        cnt_jpg_files += 1
        if cnt_jpg_files == 1:
            csv_header = 'Datum; fn ; Model; FNumber_str; FNumber; ExpoTime, ISOSpeed, AverageGray'
            csv_file.write(csv_header)
        csv_str  = pict.datum + sep + pict.fn + sep + pict.Model + sep
        csv_str += pict.FNumber_str + sep + pict.FNumber + sep
        # csv_str += '{:06.2f}'.format(pict.ExpsTime) + sep
        csv_str += str(pict.ExpsTime) + sep
        csv_str += pict.ISOSpeed + sep
        csv_str += str(pict.av_gray) + sep
        csv_str += '\n'
        csv_file.write(csv_str)
        print '>>>>', csv_str

def calc_average_graylevel():
    print '>>>>>>>> calc_average_graylevel():'
    list_of_pict.sort(key = attrgetter('Model', 'datum'))
    for pict in list_of_pict:
        image = Image.open(pict.fn).convert('L')
        im_np_array = np.array(image)
        pict.pict.av_gray = np.average(im_np_array)


#======================================================================

if __name__ == '__main__':

    root_dir, quiet, do_calc_average, do_make_batch_file, do_make_csv_file = get_opts_args()
    initialize_list_of_pict()

    # >list_of_pict< and >dict_of_pict< are global
    make_list_of_pict()

    if do_make_batch_file:
        make_rename_batch_file()

    if do_calc_average:
        av_gray = calc_average_graylevel()

    if do_make_csv_file:
        make_csv_file()
        csv_file.close()

    print '\n' * 3

    cnt_files = print_list_of_pict()
    print '\n', '{:4d}'.format(cnt_files), ' vorhanden. '
    cnt_files = print_list_of_missing_pict()
    print '\n', '{:4d}'.format(cnt_files), ' fehlen. '


    if do_make_batch_file:
        print "\n\n>" + batch_f_name + "< written. ", cnt_files, "files to rename\n"
        batch_file.close()

    print "\n\n"
    print ">", cnt_days, "days in total"
    print ">", cnt_files, "files in directory \n"
