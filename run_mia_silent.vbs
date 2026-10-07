Set WshShell = CreateObject("WScript.Shell")
Set WshEnv = WshShell.Environment("PROCESS")
WshEnv("FOR_DISABLE_CONSOLE_CTRL_HANDLER") = "1"
WshEnv("KMP_DUPLICATE_LIB_OK") = "TRUE"
WshShell.CurrentDirectory = "D:\assistant"
WshShell.Run """C:\Users\7ims (admin)\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"" main.py", 0, False
