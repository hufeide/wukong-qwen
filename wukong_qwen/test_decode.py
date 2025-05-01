#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 解码日志中的Unicode字符串

# 测试字符串
encoded_str = "\344\273\226\347\232\204\347\224\265\346\272\220\351\224\256\345\217\257\344\273\245\351\200\200\345\207\272"

# 方法1：直接解码
result1 = encoded_str.encode('latin1').decode('utf-8')
print("方法1结果:", result1)

# 方法2：使用bytes对象
result2 = bytes(encoded_str, 'latin1').decode('utf-8')
print("方法2结果:", result2)

# 测试其他常见Unicode编码
print("\n其他常用解码示例:")
print("\\u4f60\\u597d 解码结果:", "\u4f60\u597d") 