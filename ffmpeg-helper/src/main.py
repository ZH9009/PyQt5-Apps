#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2019-09-19 17:03:07
# @Author  : Lewis Tian (taseikyo@gmail.com)
# @Link    : https://github.com/taseikyo
# @Version : Python3.7

import os
import sys
import subprocess

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from mwin import Ui_MWin

DURATION_MODE = 0
ENDTIME_MODE = 1


class MWin(QMainWindow, Ui_MWin):
    def __init__(self, parent=None):
        super(MWin, self).__init__(parent)
        self.setupUi(self)

        self.cut_file_path = ''
        self.merge_files_path = ''

        self.mode = DURATION_MODE

        self.cmder_thread = Cmder('')
        self.cmder_thread.log.connect(self.log_display)
        self.cmder_thread.done.connect(self.log_display)
        self.cmder_thread.error.connect(self.error_handler)

    @pyqtSlot()
    def on_select_file_btn_clicked(self):
        filename, filetype = QFileDialog.getOpenFileName(self,
                                                         'choose file',
                                                         '.', '*')
        if not filename:
            return

        self.cut_file_path = filename
        self.filename_label.setText(os.path.basename(filename))
        self.log_edit.setPlainText('')

    def on_duration_check_stateChanged(self, mode):
        if mode == 0:
            self.mode = ENDTIME_MODE
            self.radio_label.setText('End Time:')
        else:
            self.mode = DURATION_MODE
            self.radio_label.setText('Duration:')

    @pyqtSlot()
    def on_start_btn_clicked(self):
        if not self.cut_file_path:
            return

        start_offset_raw = self.start_time_edit.text().replace('：', ':').replace(' ', '')
        end_offset_raw = self.end_time_edit.text().replace('：', ':').replace(' ', '')

        start_offset = self.time_format_check(start_offset_raw)
        end_offset = self.time_format_check(end_offset_raw)

        self.start_time_edit.setText(start_offset)
        self.end_time_edit.setText(end_offset)

        if (not start_offset) or (not end_offset):
            return

        tmp = self.filename_label.text().split('.')
        out_file = os.path.split(self.cut_file_path)[
            0] + '/' + tmp[0] + '_cut.' + tmp[1]

        if self.mode == ENDTIME_MODE:
            if not self.time_interval_check(start_offset, end_offset):
                return

            cmd = f'ffmpeg -i "{self.cut_file_path}" -vcodec copy -acodec copy -ss {start_offset} -to {end_offset} "{out_file}" -y'
        else:
            cmd = f'ffmpeg -ss {start_offset} -i "{self.cut_file_path}" -vcodec copy -acodec copy -t {end_offset} "{out_file}" -y'

        self.cmder_thread.cmd = cmd
        self.cmder_thread.start()

    @pyqtSlot()
    def on_extract_btn_clicked(self):
        if not self.cut_file_path:
            return

        path, file = os.path.split(self.cut_file_path)

        cmd = f'''ffmpeg -i "{self.cut_file_path}" -vn -y -acodec copy "{path}/{file.split('.')[0]}.m4a"'''
        self.cmder_thread.cmd = cmd
        self.cmder_thread.start()

    def time_format_check(self, time_raw):
        '''check `time_raw` is legal
        and return a legal time
        '''
        time_legal = []
        carry = 0
        for x in time_raw.split(':')[::-1]:
            try:
                tmp = int(x) + carry
                if tmp > 59:
                    carry = tmp // 60
                    tmp -= 60
                else:
                    carry = 0
                time_legal.append(str(tmp))
            except:
                return ''
        if carry:
            time_legal.append(str(carry))
        return ':'.join(time_legal[::-1])

    def time_interval_check(self, time_start, time_end):
        '''check end > start
        '''
        start, end = 0, 0
        base = 1
        for x in time_start.split(':')[::-1]:
            start += base*int(x)
            base *= 10
        base = 1
        for x in time_end.split(':')[::-1]:
            end += base*int(x)
            base *= 10
        return start < end

    @pyqtSlot()
    def on_select_files_btn_clicked(self):
        files, ok = QFileDialog.getOpenFileNames(self, 'choose file',
                                                 '.', 'MP4 Files (*.mp4)')
        if not ok:
            return
        self.merge_files_path = files

        self.tableWidget.clearContents()
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(1)
        self.tableWidget.setHorizontalHeaderLabels(['Merge Filenames'])
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

        for x in range(len(files)):
            self.tableWidget.insertRow(x)
            print(files[x])
            self.tableWidget.setItem(x, 0, QTableWidgetItem(files[x]))

    @pyqtSlot()
    def on_start_merge_btn_clicked(self):
        if not self.merge_files_path or len(self.merge_files_path) < 2:
            return

        ts_files = []
        out_dir = os.path.split(self.merge_files_path[0])[0]
        # transform
        for x in self.merge_files_path:
            tmp = os.path.split(x)
            out_file = tmp[0] + '/' + tmp[1].split('.')[0] + '.ts'
            ts_files.append(tmp[1].split('.')[0] + '.ts')
            cmd = f'ffmpeg -i "{x}" -acodec copy -vcodec copy -absf aac_adtstoasc -y "{out_file}"'
            try:
                with os.popen(cmd) as f:
                    print(f.read())
            except Exception as e:
                print(e)
                return

        cwd = os.getcwd()
        os.chdir(out_dir)
        # merge
        cmd = f'''ffmpeg -i "concat:{'|'.join(ts_files)}" -acodec copy -vcodec copy -absf aac_adtstoasc -y "{ts_files[0]}_merge.mp4"'''
        print(cmd)
        try:
            with os.popen(cmd) as f:
                print(f.read())
        except Exception as e:
            print(e)
            os.remove(f'{ts_files[0]}_merge.mp4')
            return

        # for x in ts_files:
        #     os.remove(x)

        os.chdir(cwd)


    def log_display(self, text):
        old_text = self.log_edit.toPlainText()
        self.log_edit.setPlainText(f'{old_text}{text}')        

        scrollbar = self.log_edit.verticalScrollBar()
        if scrollbar:
            scrollbar.setSliderPosition(scrollbar.maximum())

    def error_handler(self, emsg):
        QMessageBox.warning(self, 'FFmpeg Helper', emsg, QMessageBox.Ok)

class Cmder(QThread): 
    log = pyqtSignal(str)
    error = pyqtSignal(str)
    done = pyqtSignal(str)

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd
  
    def run(self):  
        try:
            p = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            for line in iter(p.stdout.readline, b''):
                try:
                    line = line.decode('utf-8')
                except:
                    line = line.decode('gbk')
                self.log.emit(line)
        except Exception as e:
            self.error.emit(str(e))
        self.done.emit('done')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MWin()
    w.show()
    sys.exit(app.exec_())
