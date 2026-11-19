import sys, pypdfium2 as p, os
d = p.PdfDocument(sys.argv[1]); pre = sys.argv[2]
for i in range(len(d)):
    d[i].render(scale=1.3).to_pil().save(f"{pre}_{i+1}.png")
print(len(d), "halaman")
