"""
Here is a simple example for a Project that uses pthread, ssl and crypto
and it uses C++17. It does have the following file structure:

 - Source/
 - Source/Main.cpp
 - Source/App.h
 - Source/App.cpp
 - Source/Pages/
 - Source/Pages/Page.h
 - Source/Pages/Page.cpp
 - Source/Data/
 - Source/Data/Serialization.h
 - Source/Data/Serialization.cpp
 - ThirdParty/
 - ThirdParty/Include/
 - ThirdParty/Include/SomeHeaderOnlyLib.h

Note that it does have the .cpps and the .hs in the same directory, but it
should work just fine if you separate them as well. Note that it also have 
nested folders with more code inside. It will work just fine as well.

Final executable will be generated at "./Bin/Build/Test.out" and the 
intermediate files will be located at "./Bin/Intermediates/".
"""
from maker import Maker


if __name__ == "__main__":
    maker = Maker()

    # This is the output file name:
    maker.output = "Test.out"
    
    # You can pass compiler and/or linker flags here:
    maker.compilerFlags += ["pthread"]
    maker.linkerFlags   += ["ssl", "crypto"]

    # Here is where your source code is located:
    maker.sourceDirs  += ["Source"]

    # And here is where your include directories are:
    maker.includeDirs += ["Source", "ThirdParty/Include"]

    # You can also change the maker.compiler, maker.cppVersion, maker.binDir
    # and maker.extraFlags. Check the maker.py implementation for details.

    ###########################################################################

    # Here is how to build it:
    maker.build()

    # You can also clear the solution:
    #maker.clear()

    # Or rebuild it...
    #maker.rebuild()