import re

def to_snake_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    s2 = s2.replace('2_d', '2d')
    s2 = s2.replace('3_d', '3d')
    s2 = s2.replace('4_d', '4d')
    
    return s2
