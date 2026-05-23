def emit(id, name, status, steps, expected, actual, reason="", fix=""):
    steps = steps.replace('\n', '\\n')
    print(f"{id}|{name}|{status}|{steps}|{expected}|{actual}|{reason}|{fix}", flush=True)
