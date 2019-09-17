# From rcludwick/depgen.py
# These functions take a dictionary of dependencies in the following way:
# depdict = { 'a' : [ 'b', 'c', 'd'],            'b' : [ 'c', 'd'],            'e' : [ 'f', 'g']            }
# has_loop() will check for dep loops in the dep dict with true or false.
# flatten() will create an ordered list of items according to the dependency structure.
# Note: To generate a list of dependencies in increasing order of dependencies, say for a build, run: flatten(MyDepDict)
import types


def _order(idepdict, val=None, level=0):
    """
    Generates a relative order in a dep dictionary
    :param idepdict: 
    :param val: 
    :param level: 
    :return: 
    """
    results = {}
    if val is None:
        for (k, v) in idepdict.items():
            for dep in v:
                results.setdefault(k, 0)
                d = _order(idepdict, val=dep, level=level+1)
                for dk, dv in d.items():
                    if dv > results.get(dk, 0):
                        results[dk] = dv

        return results
    else:
        results[val] = level
        deps = idepdict.get(val, None)
        if deps is None or deps == []:
            return {val: level}
        else:
            for dep in deps:
                d = _order(idepdict, val=dep, level=level+1)
                for dk, dv in d.items():
                    if dv > results.get(dk, 0):
                        results[dk] = dv

            return results


def _invert(d):
    """
    Inverts a dictionary
    :param d: 
    :return: 
    """
    i = {}
    for (k, v) in d.items():
        if isinstance(v, list):
            for dep in v:
                depl = i.get(dep, [])
                depl.append(k)
                i[dep] = depl
        else:
            depl = i.get(v, [])
            depl.append(k)
            i[v] = depl

    return i


def flatten(depdict):
    """
    flatten() generates a list of deps in order
    :param depdict: 
    :return: 
    """
    # Generate an inverted deplist
    ideps = _invert(depdict)

    # Generate relative order
    order = _order(ideps)

    # Invert the order
    iorder = _invert(order)

    # Sort the keys and append to a list
    output = [] 
    for key in sorted(iorder.keys()):
        output.extend(iorder[key])

    return output


def has_loop(depdict, seen=None, val=None):
    """
    Check to see if a given depdict has a dependency loop
    :param depdict: 
    :param seen: 
    :param val: 
    :return: 
    """
    if seen is None:
        for k, v in depdict.items(): 
            seen = []
            for val in v: 
                if has_loop(depdict, seen=list(seen), val=val):
                    return True
    else:
        if val in seen:
            return True
        else:
            seen.append(val)
            k = val
            v = depdict.get(k, [])
            for val in v:
                if has_loop(depdict, seen=list(seen), val=val):
                    return True

    return False 