import os
import pandas as pd
import re
import sys
import json
from pathlib import Path

import vcf
from BCBio import GFF
from Bio import SeqIO


def convert_vcf(fname):
    """Convert VCF to JSON."""
    output = []

    with open(fname) as fd:
        vcf_reader = vcf.Reader(fd)

        for record in vcf_reader:
            output.append({
                'position': record.POS,
                'variant': [v.sequence for v in record.ALT],
            })

    return json.dumps(output)

def parse_gff(fname):
    """Convert GFF to map."""
    features = []

    with open(fname) as fd:
        for record in GFF.parse(fd):
            for feature in record.features:
                features.append({
                    'id': record.id,
                    'type': feature.type,
                    'name': feature.id,
                    'start': int(feature.location.start),
                    'end': int(feature.location.end)
                })
    return features


def arrange_gff_data(features):
  """Add row number to each feature.""" 
  features.sort(key=lambda f: f['start'])

  rows = []
  for feature in features:
    if not rows:
      feature["row_cnt"] = 0
      rows.append([feature])
    else:
      found = False
      for idx, row in enumerate(rows):
        if row[-1]["end"] <= feature["start"]:
          feature["row_cnt"] = idx
          row.append(feature)
          found = True
          break
      if not found:
        feature["row_cnt"] = len(rows)
        rows.append([feature])

  return [item for row in rows for item in row]


def get_gff_data(gff_dir):
  """Returns a map with filename key and gff json data."""
  gff_map = {}
  for path in os.listdir(gff_dir):
    full_path = os.path.join(gff_dir, path)
    filename = os.path.splitext(path)[0]
    gff_map[filename] = arrange_gff_data(parse_gff(full_path))
  return gff_map


def convert_coverage(fname, genome_length):
  """Convert the read coverage to bp coverage.""" 
  csv = pd.read_csv(fname, sep='\t', index_col=0, header=0) 
  return [row[0] for row in csv.values]


def main(consensus_file, coverage_file, vcf_file, gff_directory, html_file_in, html_file_out):

    # parse the sample name
    sample_name = re.search("/samples/(.+/.+)/", vcf_file).group(1)

    # parse the consensus sequence
    consensus = next(SeqIO.parse(consensus_file, "fasta")).seq.upper()

    # parse coverage file
    coverage = convert_coverage(coverage_file, len(consensus))

    # load biodata in json format
    vcf_json = convert_vcf(vcf_file)
    gff_map = get_gff_data(gff_directory)

    embed_code = f"""
        var sample_name = \"{sample_name}\"
        var consensus = \"{consensus}\"
        var coverage = {coverage}
        var vcfData = {vcf_json}
        var gffData = {gff_map}
    """
  
    # assemble webpage
    with open(html_file_in) as fd:
        raw_html = fd.read()

    # TODO: make this more robust
    mod_html = raw_html.replace('{EXTERNAL_SNAKEMAKE_CODE_MARKER}', embed_code)

    with open(html_file_out, 'w') as fd:
        fd.write(mod_html)

if __name__ == '__main__':
    main(
        sys.argv[1], sys.argv[2], sys.argv[3],
        sys.argv[4], sys.argv[5], sys.argv[6]
    )