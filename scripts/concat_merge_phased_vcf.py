# import necessary modules
import os
import time
import argparse
import re
import gzip
import glob

#Keep track of when the script began
startTime = time.time()
char = '\n' + ('*' * 70) + '\n'

# Argparse Information
parser = argparse.ArgumentParser(description="To make subsequent analysis of the phased files easier, this step \
concatenates all phased chromosomes into a single file, then merges different concatenated samples into a single file")


parser.add_argument('phased_files_path', help='A path where all the phased files are stored. Only phased files from \
a single phasing method should be in this folder. Also, if you have .fam files and you are merging different families into \
one file, provide .fam files in this folder as well')
parser.add_argument('output_file', help='Name of output file')
parser.add_argument('--output_fam_file', help='Name of the output .fam file. If you are merging files from different \
families, provide a .fam file in the phased_files_path for each of the different files that are to be merged')
parser.add_argument('--merge_files', help='If multiple sample files need to be merged after chromosomes are combined, \
please indicate by "y"', default="n")

args = parser.parse_args()

#Create variables of each argument from argparse
filePath = args.phased_files_path.rstrip("/")
outputFile = args.output_file.rstrip(".gz")
famOutput = args.output_fam_file
mergeFiles = args.merge_files

# Create a nested Dictionary where the key is the sample ID, and the value is a dictionary where the key is the chromosome
# number and the value is the file name
nestedDict = {}
for file in glob.glob(f"{filePath}/*.gz"):
    firstSample = ""
    chromosome = ""
    with gzip.open(file, 'rt') as phasedFile:
        for line in phasedFile:
            if "##" in line:
                continue
            if "#CHROM" in line:
                lineList = line.rstrip().split("\t")
                firstSample = lineList[9]
            else:
                lineList = line.rstrip().split("\t")
                if lineList[0].isnumeric():
                    chromosome = lineList[0]
                    break
        if firstSample not in nestedDict:
            if len(chromosome) == 1:
                chromosome = "0" + chromosome
                nestedDict[firstSample] = {chromosome: file}
            else:
                nestedDict[firstSample] = {chromosome: file}
        else:
            if len(chromosome) == 1:
                chromosome = "0" + chromosome
                nestedDict[firstSample][chromosome] = file
            else:
                nestedDict[firstSample][chromosome] = file


# Create a dictionary where the key is the sample ID and the value  is a list (in chromosome order) of files to concat
filesToConcat = {}
for key, value in nestedDict.items():
    filesToConcat[key] = []
    for key2, value2 in sorted(value.items()):
        filesToConcat[key].append(value2)

# concatenate chromosome files into single files ordered by chromosome number
concatFiles = []
for key, value in filesToConcat.items():
    for file in value:
        os.system(f"gzip -d {file}")
        os.system(f"bgzip -f {file.rstrip('.gz')}")
        os.system(f"tabix -fp vcf {file}")
    tempOutput = f"/tmp/{key}_phased_combined.vcf.gz"
    files = " ".join(value)
    os.system(f"bcftools concat {files} -o {tempOutput} -O z")
    os.system(f"tabix -fp vcf {tempOutput}")
    concatFiles.append(f'{tempOutput}')

# Merge all phased, concatenated, files into one
if mergeFiles == "y":
    concatFilesString = " ".join(concatFiles)
    os.system(f"bcftools merge -m both {concatFilesString} -o {outputFile}.gz -O z")
    os.system(f"tabix -fp vcf {outputFile}.gz")
elif mergeFiles == "n":
    os.system(f"mv {tempOutput} {outputFile}.gz")

# Create a merged family file
# Create a dictionary where each sample has the rest of the family information needed for the family file
sampleDict = dict()
for file in glob.glob(f"{filePath}/*.fam"):
    with open(file) as famFile:
        for line in famFile:
            lineList = line.rstrip().split()
            sampleId = lineList[1]
            sampleDict[sampleId] = "\t".join(lineList) + "\n"

# create a sample list in the order of the vcf file
sampleList = []
with gzip.open(f"{outputFile}.gz", "rt") as vcfFile:
    for line in vcfFile:
        if line.startswith("##"):
            continue
        elif line.startswith("#CHROM"):
            sampleList = line.rstrip().split("\t")[9:]
        else:
            break

# use the sample order in the list to output each sample in order as found in the vcf file
if famOutput != None:
    with open(famOutput, "w") as output:
        for sample in sampleList:
            output.write(sampleDict[sample])

#Print message and how long the previous steps took
timeElapsedMinutes = round((time.time()-startTime) / 60, 2)
timeElapsedHours = round(timeElapsedMinutes / 60, 2)
print(f'{char}Done. Time elapsed: {timeElapsedMinutes} minutes ({timeElapsedHours} hours){char}')