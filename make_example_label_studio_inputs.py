import json
from pathlib import Path
import fire


def generate_json(example_root):
    example_data_root = Path(example_root)

    out_dicts = []
    for paper_dir in example_data_root.iterdir():
        print(paper_dir)
        out_dicts.append({
            'paper_text':open(list(paper_dir.glob('*_sentences.txt'))[0]).read(),
            'repo_url':open(paper_dir/'repository.txt').read()
        })


    json.dump(out_dicts, open('example_data.json', 'w'))


if __name__ == '__main__':
    fire.Fire(generate_json)
