import wx, os, time
import wx.grid as grid
from util import machineCom

class PrinterWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, 'CEIT Fabrication Manager', (100,100), (1050, 300))
        panel = wx.Panel(self)

        gridPanel = wx.Panel(panel)

        self.grid = grid.Grid(gridPanel)
        self.grid.SetRowLabelSize(0)
        self.grid.CreateGrid(10, 8)
        self.grid.EnableEditing(False)
        self.grid.SetSelectionMode(1)
        self.grid.EnableScrolling(True, True)

        self.grid.SetColLabelValue(0, 'Name')
        self.grid.SetColLabelValue(1, 'Time(min)')
        self.grid.SetColLabelValue(2, 'Filament (m)')
        self.grid.SetColLabelValue(3, 'Filament (g)')
        self.grid.SetColLabelValue(4, 'Material')
        self.grid.SetColLabelValue(5, 'Cost')
        self.grid.SetColLabelValue(6, 'Owner')
        self.grid.SetColLabelValue(7, 'ID')
        self.grid.AutoSize()

        sb  = wx.StaticBox(gridPanel, label='Jobs:')
        boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
        boxsizer.Add(self.grid, flag=wx.EXPAND)
        gridPanel.SetSizer(boxsizer)

        controlPanel = wx.Panel(panel)
        self.printButton = wx.Button(controlPanel, -1, '&Print',)
        self.cancelButton = wx.Button(controlPanel, -1, '&Cancel')
        self.deleteButton = wx.Button(controlPanel, -1, '&Delete')
        self.connectButton = wx.Button(controlPanel, -1, '&Connect')
        self.Bind(wx.EVT_BUTTON, self.OnPrint, self.printButton)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.cancelButton)
        self.Bind(wx.EVT_BUTTON, self.OnDelete, self.deleteButton)
        self.Bind(wx.EVT_BUTTON, self.OnConnect, self.connectButton)

        sb = wx.StaticBox(controlPanel, label='Controls:')
        boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
        boxsizer.Add(self.printButton, flag=wx.EXPAND)
        boxsizer.Add(self.cancelButton, flag=wx.EXPAND)
        boxsizer.Add(self.deleteButton, flag=wx.EXPAND)
        boxsizer.Add(self.connectButton, flag=wx.EXPAND)
        controlPanel.SetSizer(boxsizer)

        infoPanel = wx.Panel(panel)

        self.status = wx.StaticText(infoPanel, -1, 'Idle')
        font = wx.Font(15, wx.SWISS, wx.NORMAL, wx.NORMAL)
        self.status.SetFont(font)
        self.status.SetForegroundColour('dark green')
        self.progressGauge = wx.Gauge(infoPanel, -1)
        self.progressGauge.SetRange(100)
        self.timeleft = wx.StaticText(infoPanel, -1, 'Remaining: 00:00') 
        
        sb = wx.StaticBox(infoPanel, label='Status:')
        boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
        boxsizer.Add(self.status)
        boxsizer.Add(self.progressGauge)
        boxsizer.Add(self.timeleft)
        infoPanel.SetSizer(boxsizer)

        sizer = wx.GridBagSizer()
        sizer.Add(controlPanel, (0,1), span=(1,1), flag=wx.EXPAND)
        sizer.Add(infoPanel, (1,1), span=(1,1))
        sizer.Add(gridPanel, (0,3), span=(2,1), flag=wx.EXPAND)
        panel.SetSizer(sizer)

        self.ultipath = os.path.split(os.path.abspath(__file__))[0]
        self.ultipath = self.ultipath[:self.ultipath.rfind('/')+1] 

        self.joblist = []
        self.printnum = None
        self.progress = 0
        self.stage = 'Idle'
        self.mc = None
        self.gcodelist = []

        self.setup()

    def setup(self):
        self.printButton.Enable(False)
        self.cancelButton.Enable(False)
        self.deleteButton.Enable(False)

        queue = open(self.ultipath+'queue.txt', 'r')
        queuelines = queue.readlines()
        queue.close()

        for job in queuelines[4:]:
            self.joblist.append(job.split())

        if len(self.joblist):
            self.printButton.Enable(True)
            self.deleteButton.Enable(True)
        
        self.listToGrid()
        self.listToFile()
        self.monitorInfoFiles()

    def OnConnect(self, e):
        self.connectButton.Enable(False)
        self.mc = machineCom.MachineCom(port = '/dev/ttyACM0')
        while True:
            if self.mc.isClosedOrError():
                self.mc = machineCom.MachineCom(port='/dev/ttyACM0', baudrate = 115200)
            elif self.mc.isOperational():
                break
        

    def listToGrid(self):
        self.grid.ClearGrid()
        self.grid.DeleteRows(0, self.grid.GetNumberRows())
        if len(self.joblist) > 10:
            self.grid.AppendRows(len(self.joblist))
        else:
            self.grid.AppendRows(10)
        
        for i in range(len(self.joblist)):
            for j in range(len(self.joblist[i])):
                self.grid.SetCellValue(i, j, self.joblist[i][j])

        self.grid.AutoSize()
        self.grid.ForceRefresh()


    def listToFile(self):
        queuelines = []
        
        queuelines.append('//NumJobs TotalTime Status Progress\n')

        numjobs = len(self.joblist)
        
        if len(self.joblist):
            totaltime = int(int(self.joblist[0][1]) * (1-self.progress/100.0))
            for job in self.joblist[1:]:
                totaltime += int(job[1])
        else:
            totaltime = 0
            
        if self.stage == 'Idle':
            queuelines.append(str(numjobs)+'\t'+ str(totaltime) +'\t'+ self.stage +'\t'+ str(self.progress) +'\n')
        elif self.stage == 'Printing':
            queuelines.append(str(numjobs)+'\t'+ str(totaltime) +'\t'+ self.stage +self.joblist[self.printnum][7]+'\t'+ str(self.progress) + '\n')
        queuelines.append('\n')
        queuelines.append('//Name Time Fil(m) Fil(g) Mat Cost Owner ID\n')

        for job in self.joblist:
            line = ''
            for i in job:
                line += i + '\t'
            line += '\n'
            queuelines.append(line)

        queue = open(self.ultipath + 'queue.txt', 'w')
        queue.writelines(queuelines)
        queue.close()


    def monitorInfoFiles(self):
        if self.mc != None:
            statestring = self.mc.getStateString()
            print statestring
            if 'Error' in statestring:
                self.connectButton.Enable(True)
        wx.CallLater(3000, self.monitorInfoFiles)
        if os.listdir(self.ultipath+'JobInfo/') == []:
            return

        if not self.cancelButton.IsEnabled():
            self.deleteButton.Enable(True)
            self.printButton.Enable(True)

        filename = self.ultipath + 'JobInfo/' + os.listdir(self.ultipath+'JobInfo')[0]
        time.sleep(1) # wait to ensure complete transfer
        info = open(filename, 'r')
        infolist = info.readlines()
        info.close()
        os.remove(filename)
        
        for i in range(len(infolist)):
            infolist[i] = infolist[i].strip()

        self.joblist.append(infolist)
        self.listToGrid()
        self.listToFile()

    def getGcodeList(self, filename):
        prevLineType = 'CUSTOM'
        self.gcodelist = ['M110']

        for line in open(filename, 'r'):
            if line.startswith(';TYPE:'):
                lineType = line[6:].strip()
            if ';' in line:
                line = line[0:line.find(';')]
            line = line.strip()
            if len(line) > 0:
                if prevLineType != lineType:
                    self.gcodelist.append((line, lineType, ))
                else:
                    self.gcodelist.append(line)

                prevLineType = lineType

    def OnPrint(self, e):
        jobnum = self.grid.GetGridCursorRow()

        if jobnum < len(self.joblist):
            self.printnum = jobnum
            self.printButton.Enable(False)
            self.cancelButton.Enable(True)
            self.deleteButton.Enable(False)

            job = self.joblist[jobnum]
            gcode = self.ultipath + 'Jobs/' + job[0] + '.' + job[7] + '.gcode'
            self.getGcodeList(gcode)
            self.mc.printGCode(self.gcodelist)

            self.monitorProgress()

            
    def OnCancel(self, e):
        self.printButton.Enable(True)
        self.cancelButton.Enable(False)
        self.deleteButton.Enable(True)

        self.mc.cancelPrint()
        self.mc.sendCommand('G28 X0 Y0')
        self.mc.sendCommand('G1 Z10')
        self.mc.sendCommand('M106 S0')
        self.mc.sendCommand('M104 S0')
        

        self.printnum = None

    def OnDelete(self, e):
        jobnum = self.grid.GetGridCursorRow()

        if jobnum < len(self.joblist):
            job = self.joblist.pop(jobnum)
            jobfile = job[0] +'.'+ job[7] +'.gcode'
            os.remove(self.ultipath + 'Jobs/' + jobfile)
            self.listToGrid()
            self.listToFile()
            if not len(self.joblist):
                self.printButton.Enable(False)
                self.deleteButton.Enable(False)

    def monitorProgress(self):
        self.progress = int(100*self.mc.getPrintPos()/float(len(self.gcodelist)))
        self.progressGauge.SetValue(int(self.progress))
        timeleft = self.mc.getPrintTimeRemainingEstimate()
        if timeleft != None:
            self.timeleft.SetLabel('Remaining %0.2d:%0.2d' % (timeleft/60, timeleft%60))
        else:
            self.timeleft.SetLabel('Remaining: Calculating...')

        if self.mc.isPrinting():
            self.stage = 'Printing'
            self.status.SetLabel(self.stage)
            self.status.SetForegroundColour('orange')
            wx.CallLater(5000, self.monitorProgress)
        elif self.mc.isError():
            self.stage = 'Error'
            self.status.SetLabel(self.stage)
            self.status.SetForegroundColour('red')
            self.connectButton.Enable(True)
        else:
            self.stage = 'Idle'
            self.status.SetLabel(self.stage)
            self.status.SetForegroundColour('dark green')
            self.timeleft.SetLabel('Remaining: 00:00')
            self.progressGauge.SetValue(0)

            if self.printnum != None:
                job = self.joblist.pop(self.printnum)
                jobfile = job[0] + '.' + job[7] + '.gcode'
                os.remove(self.ultipath+'Jobs/'+jobfile)
                self.listToGrid()
                self.listToFile()
                self.printnum = None
                self.printButton.Enable(True)
                self.cancelButton.Enable(False)
                self.deleteButton.Enable(True)

        self.listToFile()

class UtilityWindow(wx.Frame):
    title = 'Printer Utilities'

    def __init__(self):
        wx.Frame.__init__(self, wx.GetApp().TopWidnwo, title=self.title)
        
if __name__ == '__main__':
    app = wx.PySimpleApp()
    window = PrinterWindow(None)
    window.Show()
    app.MainLoop()

            
