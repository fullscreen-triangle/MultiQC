#!/usr/bin/env python

""" MultiQC module to parse output from QualiMap """

from __future__ import print_function
from collections import defaultdict, OrderedDict
import logging
import os

from multiqc import config
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger
from multiqc.plots import linegraph
log = logging.getLogger(__name__)

class MultiqcModule(BaseMultiqcModule):
    """
    Mosdepth can generate multiple outputs with a common prefix and different endings.
    The module can use first 2, generating 2 plots for each.

    {prefix}.mosdepth.global.dist.txt
    a distribution of proportion of bases covered at or above a given threshhold for each chromosome and genome-wide

    1       2       0.00
    1       1       0.00
    1       0       1.00
    total   2       0.00
    total   1       0.00
    total   0       1.00

    {prefix}.mosdepth.region.dist.txt (if --by is specified)
    same, but in regions

    1       2       0.01
    1       1       0.01
    1       0       1.00
    total   2       0.00
    total   1       0.00
    total   0       1.00

    {prefix}.per-base.bed.gz (unless -n/--no-per-base is specified)

    1       0       881481  0
    1       881481  881482  2
    1       881482  881485  4

    {prefix}.regions.bed.gz (if --by is specified)
    the mean per-region from either a BED file or windows of specified size

    1       2488047 2488227 TNFRSF14        0.00
    1       2489098 2489338 TNFRSF14        0.00

    {prefix}.quantized.bed.gz (if --quantize is specified)
    quantized output that merges adjacent bases as long as they fall in the same coverage bins e.g. (10-20)

    1       0       881481  0:1
    1       881481  881485  1:5
    1       881485  881769  5:150

    {prefix}.thresholds.bed.gz (if --thresholds is specified) - how many bases in each region are covered at the given thresholds

    #chrom  start   end     region  1X      10X     20X     30X
    1       2488047 2488227 TNFRSF14        0       0       0       0
    1       2489098 2489338 TNFRSF14        0       0       0       0

    """

    def __init__(self):

        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='mosdepth', anchor='mosdepth',
            href="https://github.com/brentp/mosdepth",
            info="performs fast BAM/CRAM depth calculation for WGS, exome, or targeted sequencing")

        self.average_coverage_chart('global')
        self.average_coverage_chart('region')

    def average_coverage_chart(self, scope='global'):
        xmax = 0
        data = defaultdict(OrderedDict)
        avgdata = defaultdict(OrderedDict)
        for f in self.find_log_files('mosdepth/' + scope + '_dist'):
            s_name = self.clean_s_name(f['fn'], root=None)
            for line in f['f'].split("\n"):
                if "\t" not in line:
                    continue
                contig, cutoff_reads, bases_fraction = line.split("\t")
                if not contig == "total":
                    avg = avgdata[s_name].get(contig, 0) + float(bases_fraction)
                    avgdata[s_name][contig] = avg
                y = 100.0 * float(bases_fraction)
                x = int(cutoff_reads)
                data[s_name][x] = y
                if y > 1.0:
                    xmax = max(xmax, x)

            if s_name in data:
                self.add_data_source(f)

        if data:
            self.add_section(
                name='Coverage distribution (' + scope + ')',
                anchor='mosdepth-coverage-dist-' + scope,
                description='Distribution of the number of locations in the reference genome with a given depth of coverage',
                plot=linegraph.plot(data, {
                    'id': 'mosdepth-coverage-dist-id-' + scope,
                    'xlab': 'Coverage (X)',
                    'ylab': '% bases in ' + scope + ' covered by least X reads',
                    'ymax': 100,
                    'xmax': xmax,
                    'tt_label': '<b>{point.x}X</b>: {point.y}',
                })
            )
            self.add_section(
                name='Average coverage per contig (' + scope + ')',
                anchor='mosdepth-coverage-per-contig-id-' + scope,
                description='Average coverage per contig or chromosome',
                plot=linegraph.plot(avgdata, {
                    'id': 'mosdepth-coverage-per-contig-' + scope,
                    'xlab': 'region',
                    'ylab': 'average coverage',
                    'categories': True
                })
            )
