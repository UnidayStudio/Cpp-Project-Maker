# Maker - By Guilherme Teres (@UnidayStudio)
# Visit: https://github.com/UnidayStudio

import os
import ast
import shutil
import threading
import subprocess


class Maker:
    def __init__(self):
        self.compiler = "g++"
        self.cppVersion = 17

        self.compilerFlags = []
        self.linkerFlags   = []
        self.extraFlags    = []

        self.includeDirs = []
        self.sourceDirs  = []

        self.binDir = "Bin/"
        self.output = "a.out"

        self.__lastCompiledData = {}
        self.__lock = threading.Lock()

        self.__interms = ""
        self.__printLock = threading.Lock()
        self.__withError = 0
        self.__built = 0
        self.__anyHeaderChanged = False

    ###########################################################################

    def __getCppVersion(self) -> str:
        return " -std=c++%d " % self.cppVersion

    def __getIncludeDirs(self) -> str:
        out = ""
        for incl in self.includeDirs:
            out += " -I\"%s\"" % incl.replace("\\", "/")
        return out

    def __getCompilerFlags(self) -> str:
        out = ""
        for flag in self.compilerFlags:
            out += " -%s" % flag
        return out
    
    def __getLinkerFlags(self) -> str:
        out = ""
        for flag in self.linkerFlags:
            out += " -l%s" % flag
        return out

    def __getExtraFlags(self) -> str:
        out = ""
        for flag in self.extraFlags:
            out += " -%s" % flag
        return out

    ###########################################################################

    def __runCmd(self, cmd):
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
        return res

    def __needsBuilding(self, fileName: str, checkInterm=True, checkDeps=True) -> bool:
        if checkInterm:
            interm = self.__getIntermediateFileName(fileName)
            if not os.path.exists(interm):
                return True
        
        self.__lock.acquire()
        if not fileName in self.__lastCompiledData:
            self.__lock.release()
            return True
        if os.path.getmtime(fileName) > self.__lastCompiledData[fileName]:
            self.__lock.release()
            return True
        self.__lock.release()

        if checkDeps:
            res = self.__runCmd("g++ -MM \"%s\" %s" % (fileName, self.__getIncludeDirs())).stdout
            deps = res.split(".o: ")[1].replace("\n", " ").replace("\\", " ").replace("  ", " ").split(" ")
            deps = [obj.lstrip(" ").rstrip(" ") for obj in deps if obj.replace(" ", "") != ""]
            
            for dep in deps:
                if self.__needsBuilding(dep, False, False):
                    print("Dep needs build:", dep)
                    return True
        return False

    def __getIntermediateFileName(self, fileName: str) -> str:
        return self.binDir + "Intermediate/" + fileName.replace("/", "_").replace(".cpp", ".o")

    ###########################################################################

    def build(self):
        print("[Command: \033[92mBuild\033[0m...]")

        files = []
        print(" - Retrieving Source files...")
        for path in self.sourceDirs:
            for r, d, f in os.walk(path):
                for file in f:
                    if file.endswith(".c") or file.endswith(".cpp"):
                        files.append(os.path.join(r, file))

        print(" - Preparing Procedures...")
        cppVer = self.__getCppVersion()
        includeDirs = self.__getIncludeDirs()
        compilerFlags = self.__getCompilerFlags()
        linkerFlags   = self.__getLinkerFlags()
        extraFlags    = self.__getExtraFlags()

        # Creating the folders...
        def mkdir(dir):
            if not os.path.exists(dir):
                os.makedirs(dir)
        mkdir(self.binDir + "Intermediate/")
        mkdir(self.binDir + "Build/")

        self.__anyHeaderChanged = False

        # To avoid recompiling existing files...
        self.__lastCompiledData = {}
        mInfoDir = self.binDir + "Intermediate/maker.info"
        if os.path.exists(mInfoDir):
            print(" - Checking Previously Compiled Files...")
            file = open(mInfoDir, "r")
            try:
                self.__lastCompiledData = ast.literal_eval(file.read())
            except:
                print("[WARNING] Failed to read and parse maker.info file!")
            file.close()

            # I'll force a full recompilation on .h changes, to avoid any complex checks.
            for path in self.sourceDirs + self.includeDirs:
                for r, d, f in os.walk(path):
                    for file in f:
                        if file.endswith(".h") or file.endswith(".hpp"):
                            headerFile = os.path.join(r, file)
                            if self.__needsBuilding(headerFile, False, False):
                                print("[Note] Changed Header:", headerFile)
                                self.__anyHeaderChanged = True                      
                        if self.__anyHeaderChanged: break
                    if self.__anyHeaderChanged: break
                if self.__anyHeaderChanged: break

        self.__interms = ""
        self.__printLock = threading.Lock()
        self.__withError = 0
        self.__built = 0

        # Compiling everything into the intermediate files...
        print(" - Building the Intermediates...")
       
        def __buildThreadProc(threadNum, subFiles):
            for file in subFiles:
                if self.__withError > 0: 
                    break
                
                fileName = file.replace("\\", "/")
                intermName = self.__getIntermediateFileName(fileName)

                self.__lock.acquire()
                self.__interms += " \"%s\"" % intermName
                self.__lock.release()

                if self.__needsBuilding(fileName, True, self.__anyHeaderChanged):
                    cmd = self.compiler
                    cmd += " \"%s\" -c -o\"%s\"" % (fileName, intermName)
                    cmd += cppVer + includeDirs + compilerFlags + extraFlags

                    self.__printLock.acquire()
                    print("\t [\033[90mThread %d\033[0m] -> %s" % (threadNum, fileName))
                    self.__printLock.release()

                    out = self.__runCmd(cmd)
                    if out.stderr != "":
                        self.__printLock.acquire()
                        print("[\033[90mThread %d\033[0m][\033[91m COMPILATION ERROR \033[0m]" % threadNum)
                        print(out.stderr)
                        self.__printLock.release()
                        self.__withError += 1
                        break
                    self.__lock.acquire()
                    self.__lastCompiledData[fileName] = os.path.getmtime(fileName)
                    self.__built += 1
                    self.__lock.release()

        # Launching the threads...
        def split(a, n):
            k, m = divmod(len(a), n)
            return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))
        
        THREAD_COUNT = 8
        print(" - (Launching up to %d threads to Build!)" % THREAD_COUNT)

        threads = []
        subFiles = list(split(files, THREAD_COUNT))
        for n, sub in enumerate(subFiles):
            if sub == []:
                break
            else:
                t = threading.Thread(target=__buildThreadProc, args=[n + 1, sub])
                t.start()
                threads.append(t)
        
        for t in threads:
            t.join()                

        if self.__withError > 0:
            print("\t -> Error (%d)!" % self.__withError)
            print("[Build: \033[91mFAILED!\033[0m]")
            return False

        if self.__built > 0:
            print("\t -> Done Building!")

        # Updating the Headers Mod date...
        for path in self.sourceDirs + self.includeDirs:
            for r, d, f in os.walk(path):
                for file in f:
                    if file.endswith(".h") or file.endswith(".hpp"):
                        headerFile = os.path.join(r, file)
                        self.__lastCompiledData[headerFile] = os.path.getmtime(headerFile)

        outFile = self.binDir + "Build/" + self.output
        if self.__built > 0 or not os.path.exists(outFile):
            print(" - Linking...")
            # Linking everything...
            cmd = self.compiler
            cmd += self.__interms + cppVer + compilerFlags + linkerFlags + extraFlags
            cmd += " -o%s" % outFile
            out = self.__runCmd(cmd)
            if hasattr(out, "sdterr"):
                if out.sdterr != "":
                    print("[\033[91m LINKER ERROR \033[0m]")
                    print(out.stderr)
                    print("[Build: \033[91mFAILED!\033[0m]")
                    return False
            print("\t -> Done Linking!")
        else:
            print(" - There is nothing new to be built... :)")

        # Saving the Compilation data...
        file = open(mInfoDir, "w+")
        file.write(str(self.__lastCompiledData))
        file.close()
        print("[Build: \033[92mDONE!\033[0m]")
        return True

    def clear(self):
        print("[Command: \033[92mClear\033[0m...]")
        def rmdir(dir):
            if os.path.exists(dir):
                shutil.rmtree(dir)
        rmdir(self.binDir + "Intermediate/")
        rmdir(self.binDir + "Build/")
        print("[Clear: \033[92mDONE!\033[0m]")

    def rebuild(self):
        print("[Command: \033[92mRebuild\033[0m...]")
        self.clear()
        if self.build():
            print("[Rebuild: \033[92mDONE!\033[0m]")
        else:
            print("[Rebuild: \033[91mFAILED!\033[0m]")
