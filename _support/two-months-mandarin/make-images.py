#!/usr/local/bin/python3
#

# import PyPDF2
from PyPDF2 import PdfFileWriter, PdfFileReader
import copy
import pdf2image
from PIL import Image, ImageDraw
from colour import Color
import os

# manually entered this. Took about 5 mins ;)
# programmatically is not always better...
counts = [
  [1,0,0,2],
  [3,0,0,4],
  [2,2,0,1],
  [1,0,0,2],
  [0,3,0,1],
  [1,1,0,2],
  [1,1,1,2],
  [1,0,0,1],
  [1,2,0,0],
  [0,1,0,0],
  [0,3,0,2],
  [0,2,0,0],
  [1,0,3,1],
  [1,0,1,0],
  [0,1,0,2],
  [1,0,0,0],
  [1,0,1,0],
  [2,0,0,0],
  [2,5,0,1],
  [1,1,0,1],
  [2,1,0,0],
  [0,0,0,0],
  [1,0,0,2],
  [0,1,0,2],
  [2,0,0,0],
  [3,0,1,1],
  [4,0,0,1],
  [3,1,0,2],
  [3,1,0,2],
  [4,0,0,4],
  [1,1,0,0],
  [1,2,0,0],
  [2,1,0,3],
  [3,2,0,1],
  [2,2,0,1],
  [1,2,2,5],
  [5,1,7,3],
  [3,0,0,0],
  [4,11,1,2]
]

num_wo = sum(r[0] for r in counts)
num_shi = sum(r[1] for r in counts)
num_hen = sum(r[2] for r in counts)
num_ni = sum(r[3] for r in counts)

print("wo:", num_wo)
print("shi:", num_shi)
print("hen:", num_hen)
print("ni:", num_ni)

FILENAME = "counting-wo-shi-hen-ni.pdf"

with open(FILENAME, "rb") as in_f:
  input1 = PdfFileReader(in_f)
  numPages = input1.getNumPages()
  print("document has %s pages." % numPages)
  # numBoxesHorizontal = 13.5
  numBoxesVertical = 18
  pageWidth = input1.getPage(0).mediaBox.getUpperRight_x()
  pageHeight = input1.getPage(0).mediaBox.getUpperRight_y()
  boxSize = pageHeight / float(numBoxesVertical)
  numBoxesHorizontal = pageWidth / boxSize
  print(numBoxesVertical, numBoxesHorizontal)

  padding = boxSize * 0.1

  def addBox(output,pageNum,bounds):
    i, j = bounds
    page = copy.copy(input1.getPage(pageNum))
    lowerLeft = (i*boxSize - padding, j*boxSize - padding)
    upperRight = ((i+1)*boxSize + padding, (j+1)*boxSize + padding)
    page.trimBox.lowerLeft = lowerLeft
    page.trimBox.upperRight = upperRight
    page.cropBox.lowerLeft = lowerLeft
    page.cropBox.upperRight = upperRight
    output.addPage(page)


  for character in [0,1,2,3]:
    name = ["wo","shi","hen","ni"][character]
    output = PdfFileWriter()

    for pageNum in range(0, len(counts)):
      count = counts[pageNum][character]
      # print "========", count, name, "on page", pageNum
      for idx in range(0, count):
        i = 2 + 2*character
        j = 16 - 2*idx

        # special-case the last page which has too many "shi"s
        # we could say that this page is... shitty
        if (pageNum == len(counts)-1) and (character == 1) and (idx >= 8):
          i = 6
          j = 6 - 2*(idx-8)

        # print name, pageNum, i, j
        addBox(output, pageNum, (i, j))

    with open("{}.pdf".format(name), "wb") as out_f:
      output.write(out_f)

# ============================================================================
# now convert those pdfs into images

for name in ["wo","shi","hen","ni"]:
  images = pdf2image.convert_from_path('{}.pdf'.format(name), dpi=500, use_cropbox=True)
  numImages = len(images)
  red = Color("red")
  colors = list(red.range_to(Color("green"),numImages))
  for i in range(0, numImages):
    im = images[i]
    width, height = im.size
    draw = ImageDraw.Draw(im)
    thickness = 11
    (r,g,b) = colors[i].rgb
    draw.line(
      (0, height-thickness, width*(i/(numImages-1)), height-thickness),
      fill = (int(255*r), int(255*g), int(255*b)),
      width = 2*thickness
    )
    im.save('{}.{}.png'.format(name,i))

  os.system("ffmpeg -r 10 -i " + name + ".%01d.png -vcodec mpeg4 -y " + name + ".mp4")

