import json
import pytest

def test_teensy_json_formatting():
    # Example JSON string from Teensy firmware
    json_line = '{"t":123456,"ax":1.23,"ay":4.56,"az":7.89,"gx":0.12,"gy":0.34,"gz":0.56,"mx":0.01,"my":0.02,"mz":0.03,"qw":0.707,"qx":0.0,"qy":0.707,"qz":0.0}'
    data = json.loads(json_line)
    # Check all expected fields
    assert set(data.keys()) == {"t","ax","ay","az","gx","gy","gz","mx","my","mz","qw","qx","qy","qz"}
    # Check types
    assert isinstance(data["t"], int)
    for key in ["ax","ay","az","gx","gy","gz","mx","my","mz","qw","qx","qy","qz"]:
        assert isinstance(data[key], float)
    # Check values
    assert data["ax"] == 1.23
    assert data["qw"] == 0.707 