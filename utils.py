import pickle

def serialize(val):
    return pickle.dumps(val)

def deserialize(blob):
    return pickle.loads(blob)