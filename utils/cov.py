import os
import sys
import json
import subprocess
import datetime
import shutil
from shutil import copyfile


def read_file(file_path):
    content = ""
    with open(file_path) as file:
        content = file.read()
    return content


def read_json(file_path):
    data = {}
    with open(file_path) as json_file:
        data = json.load(json_file)
    return data


def generate_cover_letter(cover_letter_name, global_data, local_data, content_fp, out_file, template_dir='template'):
    data = global_data.copy()
    if "date" not in local_data:
        now = datetime.datetime.now()
        local_data["date"] = now.strftime("%B %d, %Y")

    data["cl_data"] = local_data

    tmp_dir = os.path.join(template_dir, 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    copyfile(content_fp, os.path.join(tmp_dir, 'content.md'))

    pro = subprocess.Popen(["relaxed", os.path.join(template_dir, "cover_letter.pug"),
                            out_file, "--temp", tmp_dir, "--build-once", "--locals", json.dumps(data)])

    import time
    time.sleep(10)

    import signal
    try:
        os.killpg(pro.pid, signal.SIGTERM)
    except:
        print("Done!")


if __name__ == '__main__':
    os.makedirs("output", exist_ok=True)
    os.makedirs("template/tmp", exist_ok=True)
    generate_cover_letter("let1", read_json('info.json'), read_json(
        './cover_letters/info.json'), './cover_letters/content.md', './output/cover-letter.pdf')
    shutil.rmtree("template/tmp")
