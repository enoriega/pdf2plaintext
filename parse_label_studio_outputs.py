from typing import NamedTuple, Hashable
from collections import defaultdict
import sys
import json
import regex
import uuid
import functools
import fire
import os


class TextSegment(NamedTuple):
    uuid: str
    source_name: Hashable
    start: int
    end: int
    text: str

    def __eq__(self, other) -> bool:
        return self[1:].__eq__(other[1:])

    def __hash__(self) -> int:
        return hash(self[1:])


class CodeSegment(NamedTuple):
    uuid: str
    url: str
    repo: str
    hash: str
    file: str
    start_line: int  # line number, index starting with 1, as in github convention
    end_line: int  # line number, end-inclusive, as in github convention

    def __eq__(self, other) -> bool:
        return self[1:].__eq__(other[1:])

    def __hash__(self) -> int:
        return hash(self[1:])


class TextCodeMapping(NamedTuple):
    text_uuid: str
    code_uuid: str


def build_github_snippet_url_re():
    re_repo = r'(?P<repo>[^/]+/[^/]+)'
    re_git_hash = r'(?P<hash>\w{40})'
    re_file = r'(?<file>[^#]+)'
    re_line = r'#LL?(?P<start_line>\d+)(C\d+)?(-L(?P<end_line>\d+))?(C\d+)?'

    re_snippet = f"https://github\.com/{re_repo}/blob/{re_git_hash}/{re_file}{re_line}$"
    return regex.compile(re_snippet)


def parse_label_studio_out(paper_outputs, paper_name, output_dir='./'):
    text_segment_by_text_offsets = dict()
    code_segment_set_by_text_offsets = defaultdict(set)
    text_code_mappings = set()

    re_github_snippet_url = build_github_snippet_url_re()

    for output in paper_outputs:
        new_uuid_str = uuid.uuid4().hex
        match output['from_name']:
            case 'text_segment':
                text_segment_by_text_offsets[(output['value']['start'], output['value']['end'])] = \
                        TextSegment(
                            uuid=new_uuid_str,
                            source_name=paper_name,
                            start=output['value']['start'],
                            end=output['value']['end'],
                            text=output['value']['text'],
                        )
            case 'snippet_github_url':
                for snippet_url in output['value']['text']:
                    snippet_url_match = re_github_snippet_url.search(snippet_url)
                    if snippet_url_match is None:
                        print(f'unparsable url "{snippet_url}"', sys.stderr)
                        continue

                    code_segment_set_by_text_offsets[(output['value']['start'], output['value']['end'])].add(
                            CodeSegment(
                                uuid=uuid.uuid4().hex,
                                url=snippet_url,
                                repo=snippet_url_match['repo'],
                                file=snippet_url_match['file'],
                                hash=snippet_url_match['hash'],
                                start_line=int(snippet_url_match['start_line']),
                                end_line=int(snippet_url_match['start_line'] if snippet_url_match['end_line'] is None else snippet_url_match['end_line']),
                            )
                    )

    for text_offsets, code_segment_set in code_segment_set_by_text_offsets.items():
        for code_segment in code_segment_set:
            text_code_mappings.add(
                    TextCodeMapping(
                        text_uuid=text_segment_by_text_offsets[text_offsets].uuid,
                        code_uuid=code_segment.uuid,
                    )
            )

    paper_dir = f'{output_dir}/{paper_name}'
    os.mkdir(paper_dir)
    json.dump(
            [text_segment._asdict() for text_segment in text_segment_by_text_offsets.values()],
            open(f'{paper_dir}/text_segments.json', 'w')
    )
    json.dump(
            [code_segment._asdict() for code_segment in functools.reduce(set.union, code_segment_set_by_text_offsets.values())],
            open(f'{paper_dir}/code_segments.json', 'w')
    )
    json.dump(
            [text_code_mapping._asdict() for text_code_mapping in text_code_mappings],
            open(f'{paper_dir}/text_code_mapping.json', 'w')
    )


def parse_json(input_path, output_dir):
    for paper in json.load(open(input_path)):
        repo_name = regex.search(r'(?<=github\.com/[^/]+/)[^/]+', paper['data']['repo_url']).group()
        parse_label_studio_out(paper['annotations'][0]['result'], repo_name, output_dir=output_dir)


if __name__ == '__main__':
    fire.Fire(parse_json)

