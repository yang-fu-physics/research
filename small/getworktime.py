from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QTextCursor
from PySide6 import QtCore
import time
import threading
class Stats:

    def __init__(self):
        # 从文件中加载UI定义
        # 从 UI 定义中动态 创建一个相应的窗口对象
        # 注意：里面的控件对象也成为窗口对象的属性了
        # 比如 self.ui.button , self.ui.textEdit
        self.ui = QUiLoader().load('C:\\'
                                   'Users\\Admin\\Desktop\\研究生\\python\\111\\small\\11.ui')
        self.starttime=0
        self.stoptime=0
        self.time = 0
        self.newday=True
        with open("work.txt") as f:
            self.ui.text.setPlainText(f.read())
        self.localtime = time.localtime(time.time())
        self.ui.start.clicked.connect(self.getstarttime)
        self.ui.stop.clicked.connect(self.getstoptime)
        self.ui.time.setText("")
        #self.ui.reset.clicked.connect(self.reset)
        self.Staus = False
        self.ui.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
    def getstarttime(self):
        self.starttime=time.time()
        self.Staus=True
        if self.localtime[0:3] != time.localtime(time.time())[0:3]:
            self.time=0
            self.localtime = time.localtime(time.time())
            self.newday=True
        self.ui.ing.setText(" work")
    def getstoptime(self):
        #self.ui.text.reload()
        self.Staus=False
        with open("work.txt", "a+") as m:
            m.write(time.asctime(self.localtime) + "\t%i小时%i分钟%i秒\n" % (
            self.time // 3600, self.time % 3600 // 60, self.time % 3600 % 60))
        with open("work.txt") as f:
            self.ui.text.setPlainText(f.read())
        self.ui.ing.setText("break")
        self.ui.text.moveCursor(QTextCursor.End)
        #self.ui.text.centerCursor()
        #ensureCursorVisible()



app = QApplication([])
stats = Stats()
stats.ui.show()
a=True
def b():
    while a:
        if stats.Staus:
            time.sleep(1)
            newtime=time.time()
            stats.time=time.time()-stats.starttime+stats.time
            stats.starttime=newtime
            stats.ui.bar.setValue(int(stats.time / (8*36)))
            stats.ui.time.setText("\t%i小时%i分钟%i秒" % (
            stats.time // 3600, stats.time % 3600 // 60, stats.time % 3600 % 60))
        else:
            time.sleep(1)
            #print(stats.Staus)
b=threading.Thread(target=b)
b.start()
app.exec_()
a=False
time.sleep(60)
