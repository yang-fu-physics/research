import PyPDF2
import re
import os
def fnPDF_FindText(xFile, xString):
    # xfile : the PDF file in which to look
    # xString : the string to look for
    PageFound = []
    pdfDoc = PyPDF2.PdfFileReader(open(xFile, "rb"))
    for i in range(0, pdfDoc.getNumPages()):
        content = ""
        content += pdfDoc.getPage(i).extractText() + "\n"
        content1 = content.encode('ascii', 'ignore').lower()
        content2 = content1.decode("utf-8")
        #print(content2)
        ResSearch = re.search(xString, content2)
        if ResSearch is not None:
            #print(ResSearch)
            PageFound.append(i)
        #print(i)
        #print(PageFound)
    return PageFound


def fnPDF_ExtractPages(xFileNameOriginal, xFileNameOutput, xPage):
    from PyPDF2 import PdfFileReader, PdfFileWriter
    output = PdfFileWriter()
    pdfOne = PdfFileReader(open(xFileNameOriginal, "rb"))
    for i in xPage:
        #print(i)
        #print(xFileNameOutput)
        output.addPage(pdfOne.getPage(i))
        outputStream = open(xFileNameOutput, "wb")
        output.write(outputStream)
        outputStream.close()

workdir = r'C:\Users\Admin\Desktop\11774423'
file = [entry.path for entry in os.scandir(workdir) if entry.name.endswith(".pdf")]
file.sort(reverse=True)
k=0
"""for i in file:
    m = i.strip().split('\\')[-1]
    file[k]=m.strip().split('.')[0]
    k=k+1
print(file)"""
m=1
error=[]
more=[]
for i in file:
    ss=i.strip().split('\\')[-1]
    newfile= ss.strip().split('.')[1:]
    newfilename=""
    for j in newfile:
        newfilename=newfilename+j+"."
    newfilename=newfilename[:-1]
    print(ss)
    newfilename2='C:\\Users\\Admin\\Desktop\\11774423-2\\'+str(m)+"."+newfilename
    pagenum=fnPDF_FindText(i,'11774423')
    #print(pagenum)
    if len(pagenum)==0:
        error.append(ss+"("+str(m)+")")
    elif len(pagenum)>1:
        more.append(ss)
    else:
        if pagenum[0]!=0:
            pagenum.insert(0,0)
    fnPDF_ExtractPages(i,newfilename2,pagenum)
    m=m+1
print("error：以下未找到：")
print(error)
print("以下多于一个：")
print(more)