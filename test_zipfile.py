import os
from zipfile import ZipFile

zipfile_name = "forma_file.zip"

if (os.path.exists(zipfile_name)):
    os.remove(zipfile_name)

zf = ZipFile(zipfile_name, 'w')
zf.close()

zf = ZipFile(zipfile_name, 'a')
zf.write("format.ased", "format files/format.ased")
zf.close()
