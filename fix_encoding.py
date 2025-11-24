# -*- coding: utf-8 -*-
import codecs

# Read with wrong encoding and write with correct UTF-8
with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix common encoding issues
replacements = {
    'Ă': 'ł',
    'Ĺ': 'ł',
    'Ä': 'ą',
    '™': 'ę',
    'Ľ': 'ż',
    'ĹĽ': 'ż',
    'Ä™': 'ę',
    'Ä…': 'ą',
    'Ĺ‚': 'ł',
    'Ĺ›': 'ś',
    'Ä‡': 'ć',
    'Ĺ„': 'ń',
    'Ăł': 'ó',
    'ĹŹ': 'ź',
    'Ä': 'ą',
    '…': 'ą',
    'Ĺ': 'ł',
    'Ĺ': 'ś',
    '›': 'ś',
    '„': 'ń',
    'Äť': 'ě',
    'Ôöť': '├',
    'ÔöÇ': '─',
    'Ôöé': '│',
    'Ôöö': '└',
    '┼é': 'ł',
    '─ů': 'ą',
    '├│': 'ó',
    '┼ä': 'ń',
    '┼Ť': 'ś',
    '┼╝': 'ż',
    'Ôöé': '│',
    'ÔöÇ': '─',
    'Ôöť': '├',
    'Ôöö': '└',
}

for wrong, correct in replacements.items():
    content = content.replace(wrong, correct)

# Write back with proper UTF-8 encoding
with open('README.md', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("Encoding fixed!")
