from string_theory.condition import Condition

grammar = {
    '<start>': ['<config>'],
    '<config>': ['<statement>', '<statement>; <config>'],
    '<statement>': ['<key>: <int>'],
    '<key>': ['name', 'date', 'time'],
    '<int>': ['<digit>', '<digit><int>'],
    '<digit>': list('0123456789'),
}

value_over_nine = Condition('returned early')
c_resolve_conflict = Condition('resolved conflict')
c_name = Condition('processed name')

def parse_config(config: str) -> dict:
    entries = (e.split(': ') for e in config.split('; '))

    result = {}

    for index, entry in enumerate(entries):

        key, value = entry
        value = int(value)

        if value > 9:
            value_over_nine.trigger()

        if key not in result:
            result[key] = value
        else:
            c_resolve_conflict.trigger()
            old = result[key]
            result[key] = max(old, value)
    
    if "name" in result:
        c_name.trigger()
    
    return result
