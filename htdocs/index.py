#!/usr/bin/env python3
# -*- coding: UTF-8 -*-# enable debugging
import cgitb
cgitb.enable()
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root+"/app/")
print("Content-Type: text/html;charset=utf-8")
print()
print("<h1 style='color:rgb(0,123,167);'>Hello World!</h1>")
print(root)


