#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Fix remaining encoding issues in README.md
with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Count original issues
original_count = content.count('â€')

# Additional fixes for remaining corrupted sequences
fixes = [
    ('â„˘', '™'),
    ('â€ž', '"'),
    ('â€ť', '"'),
    ('â€"', '—'),
    ('â…', '|'),
    ('â€'', '-'),
]

# Apply other fixes
fixed_count = 0
for wrong, right in fixes:
    if wrong in content:
        count = content.count(wrong)
        content = content.replace(wrong, right)
        print(f"Fixed '{wrong}' -> '{right}' ({count} times)")
        fixed_count += count

# Write corrected content
with open('README.md', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print(f"\n✓ Fixed {fixed_count} encoding issues!")
print(f"Remaining 'â€' sequences: {content.count('â€')}")
