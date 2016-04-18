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
# 2. CSV File zu erstellen mit fn, Uhrzeit, ExposureTime, F und ISOSpeed
#
# Output:
# 1. neuen Filenamen samt Path 
# 2. (Batchfile)
#
# https://pypi.python.org/pypi/ExifRead
#
import csv
import sys
import exifread
from datetime import datetime, time
import datetime
import os
import pprint
import re
# https://books.google.de/books?id=YRHSCgAAQBAJ&pg=PA96&lpg=PA96&dq=pil+average+grayscale&source=bl&ots=tsJ8nbYvua&sig=OHKPOAlTMV08S-p5jS-t_RacTS0&hl=de&sa=X&ved=0ahUKEwjrxo2I2JHMAhWEJhoKHY_rB0cQ6AEIRzAE#v=onepage&q=pil%20average%20grayscale&f=false
import numpy as np
from PIL import Image

do_write_batch_file = False
do_write_csv_file   = False

## TODO list of pictures:
## Für jedes Bild soll ein Objekt (iS eines -> data members) angelegt werden, das in einer Liste landet.
## Listen von Data member kann man auch gut sortieren:
##   http://stackoverflow.com/questions/403421/how-to-sort-a-list-of-objects-in-python-based-on-an-attribute-of-the-objects
## TODO dummy Bilder für die fehlenden Bilder erzeugen:
## Geht mit pil

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
    msg += '  -d --dir=     directory.\n'
    msg += '  -q --quiet    quiet (default)\n'
    msg += '\n'
    print msg
    if exit_status:
        sys.exit(exit_status)

# http://www.tutorialspoint.com/python/python_classes_objects.htm
class PictClass():
    def __init__(self, datum):
        self.datum        = datum
        self.date         = ''
        self.Make         = 'rh'
        self.Model        = ''
        self.date         = ''
        self.fn           = ''
        self.path_fn      = ''
        self.FNumber      = ''
        self.ExposureTime = ''
        self.ISOSpeed     = ''
        self.av_gray      = ''

    def __repr__(self):
        return '"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s"' % ( \
        self.datum , \
        self.Make , \
        self.Model , \
        self.date , \
        self.fn , \
        self.path_fn , \
        self.FNumber , \
        self.ExposureTime , \
        self.ISOSpeed , \
        self.av_gray )

def make_list_of_pict():
    # >list_of_pict< and >dict_of_pict< are global
    date1 = '2013_04_07'
    date2 = '2014_08_16'
    start = datetime.datetime.strptime(date1, '%Y_%m_%d')
    end   = datetime.datetime.strptime(date2, '%Y_%m_%d')
    step = datetime.timedelta(days=1)
    act_day = start
    while act_day <= end:
        act_day_str = act_day.date().strftime('%Y_%m_%d')  # Formatieren
        pict = PictClass(act_day_str)
        list_of_pict.append(pict)
        dict_of_pict.update({act_day_str : pict})
        act_day += step

def print_list_of_pict():
    for pict in list_of_pict:
        # pprint.pprint(pict)
        print(pict)

def print_list_of_missing_pict():
    for pict in list_of_pict:
        if pict.Make == 'rh':
            print(pict)

def calc_average_graylevel(fn):
    image = Image.open(fn).convert('L')
    im_np_array = np.array(image)
    return np.average(im_np_array)

#======================================================================

if __name__ == '__main__':
    import os
    import sys
    import getopt
    from os.path import basename
    from os.path import splitext

    stop_tag = 'UNDEF'
    quiet = True
    quiet = False
    root_dir = ''

    # parse command line options/arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], "d:hvrpq", ["dir=", "verbose", "nopicasa", "quiet"])
    except getopt.GetoptError:
        usage(2)
    if not args:
        usage(0)

    for o, a in opts:
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
        print 'Directory >' + root_dir +'< does not exist.'
        sys.exit(2)

    csv_f_name   = 'photos_values.csv'
    csv_f_name   = os.path.join(root_dir, csv_f_name)

    make_list_of_pict()

    if do_write_batch_file:
        try:
            batch_f_name = 'rename_photos.bat'
            batch_f_name = os.path.join(root_dir, batch_f_name)
            batch_file=open(batch_f_name, 'wb')
        except:
            print "'%s' is unwritable\n"%batch_f_name
            sys.exit(2)

    if do_write_csv_file:
        try:
            csv_f_name = 'photos_values.csv'
            csv_f_name = os.path.join(root_dir, csv_f_name)
            csv_file=open(csv_f_name, 'wb')
        except:
            print "'%s' is unwritable\n"%csv_f_name
            sys.exit(2)


    cnt_jpg_files = 0
    reg_hhmm = re.compile(r"^\d{4}_[A-Za-z]")  #

    root, dirs, files = os.walk(root_dir).next()

    for f_name in files:
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
                im_file=open(path_f_name, 'rb')
            except:
                print "'%s' is unreadable\n"%path_f_name
                continue
            # get EXif tags:
            data = exifread.process_file(im_file, details=False, stop_tag='DateTimeOriginal')
            im_file.close()

            for key in data.keys():
                if key.find('Item') >= 0:
                    Item = data[key].printable

                if key.find('Make') >= 0:
                    Make = data[key].printable # Manufacturer
                    print 'Make =', Make

                if key.find('Model') >= 0:
                    Model = data[key].printable
                    print 'Model =', Model

                if key.find('FNumber') >= 0:
                    FNumber = data[key].printable
                    print 'FNumber =' , FNumber
                    pos_slash = FNumber.find('/')
                    if pos_slash > 0:
                        counter     = FNumber[:pos_slash]
                        denominator = FNumber[pos_slash + 1:]
                        FNumber     = str (float(counter)/float(denominator))
                        print 'FNumber =', FNumber

                if key.find('ExposureTime') >= 0:
                    ExposureTime = data[key].printable
                    print 'ExposureTime =', ExposureTime,
                    pos_slash = ExposureTime.find('/')
                    if pos_slash > 0:
                        z = ExposureTime[:pos_slash]
                        n = ExposureTime[pos_slash + 1:]
                        ExposureTime_float = float(z)/float(n)
                    print '= ', ExposureTime_float, ' (', type (ExposureTime_float)

                if key.find('ISOSpeed') >= 0:
                    ISOSpeed = data[key].printable
                    print 'ISOSpeed =', ISOSpeed

                if key.find('DateTimeOriginal') >= 0:
                    date_time_str = data[key].printable
                    hhmm_prefix = date_time_str[11:13] + date_time_str[14:16]
                    hhmm_prefix = hhmm_prefix.replace(' ', '0', -1)

                    Y_M_D_prefix = date_time_str[0:4] + '_' + date_time_str[5:7] + '_' + date_time_str[8:10]
                    YMDHm_prefix = Y_M_D_prefix  + '_' + hhmm_prefix
                    if not quiet: print Y_M_D_prefix, YMDHm_prefix
                    if re.match(reg_hhmm, f_name):  # re.match == regex am Stringanfang?
                        new_f_name = YMDHm_prefix + '_' + f_name[5:]
                    else:
                        new_f_name = YMDHm_prefix + '_' + f_name

            # av_gray = calc_average_graylevel(path_f_name)
            av_gray = 99

            new_path_f_name = os.path.join(root, new_f_name)
            batch_str = 'mv %s %s ' % (path_f_name, new_path_f_name)
            # f_name = basename(path_f_name)

            pict = dict_of_pict[Y_M_D_prefix]

            # pict.datum    = datum
            pict.date     = Y_M_D_prefix
            pict.fn       = new_f_name
            pict.Make     = Make
            pict.Model    = Model
            pict.fn       = new_f_name
            pict.path_fn  = new_path_f_name
            pict.FNumber  = FNumber
            pict.ExposureTime = ExposureTime
            pict.ISOSpeed = ISOSpeed
            pict.av_gray  = av_gray

            if do_write_batch_file:
                batch_file.write(batch_str + '\n')

            try:
                print '1:[ ', FNumber, ExposureTime, ISOSpeed, '] ',
                try:
                    FN_2 = str((float(FNumber) * float(FNumber)))
                    print '2:[ ', FNumber, FN_2 , ExposureTime, ISOSpeed, ']' ,
                    # FN_2_div_t = float (FN_2) / float (ExposureTime)
                    FN_2_div_t = float (FN_2) / ExposureTime_float
                    # print '[ ', float (FN_2) / float (ExposureTime), ']' ,
                    print '3:[ ', '{:06.2f}'.format(FN_2_div_t), ']' ,
                    FN_2_div_t_times_ISO = FN_2_div_t / float (ISOSpeed)
                    print '4:[ ', '{:.0f}'.format(FN_2_div_t_times_ISO), ']' ,
                except:
                    FN_2                 = '9999'
                    FN_2_div_t           = '9999'
                    FN_2_div_t_times_ISO = '9999'
                    print '[?]'
                finally:
                    print
            except:
                pass
            finally:
                pass

            sep = ' ; '

            # csv_str =  str(cnt_jpg_files) + sep + new_f_name + sep + Model + sep
            csv_str =  new_f_name + sep + Model + sep
            csv_str += FNumber + sep + ExposureTime + sep + ISOSpeed + sep
            csv_str += '>' + sep + FNumber + sep + FN_2 + sep
            csv_str += '{:2.5f}'.format(ExposureTime_float) + sep + ISOSpeed + sep
            csv_str += '{:06.2f}'.format(FN_2_div_t) + sep + '{:.0f}'.format(FN_2_div_t_times_ISO) + sep
            csv_str += '{:.0f}'.format(av_gray) + sep + '\n'
            print '>>>>',  csv_str

            if do_write_csv_file:
                csv_file.write (csv_str)

    print_list_of_pict()
    print '\n' * 3
    print_list_of_missing_pict()

    if do_write_batch_file:
        print "\n\n>" + batch_f_name + "< written. ", cnt_jpg_files, "files to rename\n"
        batch_file.close()
    if do_write_csv_file:
        csv_file.close()

    print "\n\n>", cnt_jpg_files, "files in directory \n"
