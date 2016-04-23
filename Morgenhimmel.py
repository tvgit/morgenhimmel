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
# 4. Fehlende Bilder ersetzen (496 = 2**4  * 31)  # 497 möglich
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
import pprint
import random
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
do_make_new_images = False

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
    msg += '  -s --syn      synthesize new images\n'
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
        opts, args = getopt.getopt(sys.argv[1:], "acbd:hvqs", ["avrge", "csv", "batch", "dir=", "verbose", "quiet", "syn"])
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
        if o in ("-s", "--syn"):
            do_make_new_images = True
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
        self.fn_old      = '0900_IMG_rh.JPG'
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
    # txt='2013_09_17_1937_IMG_9930.JPG'
    # m = rgx.search(txt)
    # if m: print 'ok'
    return rgx

def print_list_of_pict():
    list_of_pict.sort(key = attrgetter('Model', 'datum'))
    cnt_files = 0
    for pict in list_of_pict:
        # pprint.pprint(pict)
        if pict.Model != 'rh':
            cnt_files += 1
            # print '{:4d}'.format(cnt_files), pict
        else:
            print '    ', pict
            pass
    return cnt_files

def print_list_of_missing_pict():
    cnt_files = 0
    for pict in list_of_pict:
        if pict.Make == 'rh':
            # print(pict)
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

def make_list_of_pict_via_EXIF():
    # >list_of_pict< and >dict_of_pict< are global
    stop_tag = 'UNDEF'
    reg_hhmm  = re.compile(r"^\d{4}_[A-Za-z]")
    reg_YMDHm = make_regex_YMDHm_word()#
    # reg_YYYY_MM_DD_hhmm = re.compile(r"^\d{4}_[A-Za-z]")  #
    cnt_jpg_files = 0
    root, dirs, files = os.walk(root_dir).next()  # only first level
    for f_name in files:  # only files
        path_f_name = os.path.join(root, f_name)
        ext = os.path.splitext(path_f_name)[-1].lower()
        if ext == ".jpg":
            cnt_jpg_files += 1
            # print '\n', '{:4d}'.format(cnt_jpg_files), ': ', f_name

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
                    # print 'Make =', Make

                if key.find('Model') >= 0:
                    Model = data[key].printable
                    # print 'Model =', Model

                if key.find('FNumber') >= 0:
                    FNumber_str = data[key].printable
                    # print 'FNumber =', FNumber_str
                    pos_slash = FNumber_str.find('/')
                    if pos_slash > 0:
                        counter = FNumber_str[:pos_slash]
                        denominator = FNumber_str[pos_slash + 1:]
                        FNumber = str(float(counter) / float(denominator))
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
                    date_time_str = data[key].printable
                    hhmm_prefix = date_time_str[11:13] + date_time_str[14:16]
                    hhmm_prefix = hhmm_prefix.replace(' ', '0', -1)

                    Y_M_D_prefix = date_time_str[0:4] + '_' + date_time_str[5:7] + '_' + date_time_str[8:10]
                    YMDHm_prefix = Y_M_D_prefix + '_' + hhmm_prefix
                    if not quiet: print Y_M_D_prefix, YMDHm_prefix
                    if re.match(reg_hhmm, f_name):  # re.match == regex am Stringanfang?
                        new_f_name = YMDHm_prefix + '_' + f_name[5:]
                    elif reg_YMDHm.search(f_name):
                        new_f_name = YMDHm_prefix + '_' + f_name[16:]
                    else:
                        new_f_name = YMDHm_prefix + '_' + f_name

            # f_name = basename(path_f_name)
            pict = dict_of_pict[Y_M_D_prefix]
            # pict.datum    = datum
            if pict.date:
                print '!!! >>>> ', pict.date, '!!! >>>> '
                pass
            else:
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


    cnt_jpg_files = 0
    for pict in list_of_pict:
        if pict.Make != 'rh':
            cnt_jpg_files += 1

    for pict in list_of_pict:
        if pict.Model == 'rh':  # == missing images == to be synthesized
            pict.fn = pict.datum + '_' + pict.fn_old
            pict.date = pict.datum
            pict.Make = 'rh'
            pict.Model = 'rh'

    return cnt_jpg_files

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
        # print '>>>>', csv_str

def calc_average_graylevel():
    # print '>>>>>>>> calc_average_graylevel():'
    list_of_pict.sort(key = attrgetter('Model', 'datum'))
    for pict in list_of_pict:
        image = Image.open(pict.fn).convert('L')
        im_np_array = np.array(image)
        pict.pict.av_gray = np.average(im_np_array)

def calc_model_type_picts():
    # calc's number of images per model
    dict_model_cnt = {}
    list_of_pict.sort(key=attrgetter('Model', 'datum'))
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
    return list_model_cnt

def split_and_combine_rgb_channels(fn_img_new, fn_img_1, fn_img_2, fn_img_3):
    im = Image.open(fn_img_1)
    red, g, b = im.split()
    im.close()
    im = Image.open(fn_img_2)
    r, green, b = im.split()
    im.close()
    im = Image.open(fn_img_3)
    r, g, blue = im.split()
    im.close()

    img = Image.merge("RGB", (r, g, b))
    img.save(fn_img_new)

def make_result_path (dir, fn):
    return os.path.join(root_dir,dir, fn)

def make_new_images():
    res_dir = 'result_new_images'
    list_model_cnt = calc_model_type_picts()
    iter_list_model_cnt = iter(list_model_cnt)  # convert to iterator
    model, cnt_g1X = iter_list_model_cnt.next() # idx in list_of_pict of last G1X pict
    model, cnt_g15 = iter_list_model_cnt.next() #
    # cnt_g1X + cnt_g15 == 100%  = 0 .. 1.0
    cut =  float(cnt_g1X) / (float(cnt_g15) + float(cnt_g1X))
    list_of_pict.sort(key=attrgetter('Model', 'datum'))  # in place

    log_fn = 'new_images.log'
    log_f  = open(make_result_path(res_dir, log_fn), 'w')

    cnt = 0

    for pict in list_of_pict:
        if pict.Model == 'rh':   # find fn of next image to synthesize
            cnt += 1
            if random.random() < cut:
                low = 1
                high = cnt_g1X - 1
            else:
                low  = cnt_g1X
                high = cnt_g1X + cnt_g15 - 1

            # print 'pict.fn = ', pict.fn
            fn_img_new = make_result_path(res_dir, pict.fn )

            idx = int(round(random.uniform(low, high)))
            mod_1  = list_of_pict[idx].Model
            fn_1   = list_of_pict[idx].fn
            p_fn_1 = make_result_path('', fn_1)

            idx = int(round(random.uniform(low, high)))
            mod_2  = list_of_pict[idx].Model
            fn_2   = list_of_pict[idx].fn
            p_fn_2 = make_result_path('', fn_2)

            idx = int(round(random.uniform(low, high)))
            mod_3  = list_of_pict[idx].Model
            fn_3   = list_of_pict[idx].fn
            p_fn_3 = make_result_path('', fn_3)
            # print fn_img_new, fn_1, fn_2, fn_3
            log_f.write (str(cnt) + ' ; ' + fn_img_new + ' ; ')
            log_f.write (mod_1 + ' ; '  + fn_1 + ' ; ')
            log_f.write (mod_2 + ' ; '  + fn_2 + ' ; ')
            log_f.write (mod_3 + ' ; '  + fn_3 + ' ; ')
            log_f.write ('\n')
            split_and_combine_rgb_channels(fn_img_new, p_fn_1, p_fn_2, p_fn_3)

    log_f.close()
    # print cut, cnt_g1X, cnt_g15, list_of_pict[cnt_g1X - 1].fn

#======================================================================
if __name__ == '__main__':

    root_dir, quiet, do_calc_average, do_make_batch_file, do_make_csv_file = get_opts_args()
    initialize_list_of_pict()

    # >list_of_pict< and >dict_of_pict< are global
    cnt_jpg_files = make_list_of_pict_via_EXIF()

    if do_make_batch_file:
        make_rename_batch_file()

    if do_calc_average:
        av_gray = calc_average_graylevel()

    if do_make_csv_file:
        make_csv_file()
        csv_file.close()

    cnt_existing_files = print_list_of_pict()
    cnt_missing_files  = print_list_of_missing_pict()
    ## print '\n', '{:4d}'.format(cnt_missing_files), ' fehlen. '

    if do_make_batch_file:
        print "\n\n>" + batch_f_name + "< written. ", cnt_files, "files to rename\n"
        batch_file.close()

    print "\n\n"
    print ">", cnt_days, "days in total"
    print ">", cnt_existing_files, "files in directory \n"
    print ">", cnt_jpg_files, "jpg files in directory \n"
    if do_make_new_images:
        make_new_images()

    list_model_cnt = calc_model_type_picts()
    for model, cnt in list_model_cnt:
        print model + ':', cnt
    print ">", cnt_missing_files,  "missing files in directory \n"
    # print ">", cnt_files, "files in directory \n"
