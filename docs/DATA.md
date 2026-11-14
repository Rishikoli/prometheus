# Getting the data

The real run uses three tables from **PatentsView** (US patents granted since 1976). Put them, uncompressed and
tab-separated, in `data/raw/`:

| File | Used for | Columns the pipeline looks for |
|---|---|---|
| `g_patent.tsv` | grant year | `patent_id`, `patent_date` |
| `g_cpc_current.tsv` | classification | `patent_id`, `cpc_subclass`, and if present `cpc_sequence`, `cpc_type` |
| `g_us_patent_citation.tsv` | "builds on" links | `patent_id`, `citation_patent_id` |
| `g_cpc_title.tsv` (optional) | field titles | `cpc_subclass`, and a column named like `cpc_subclass_title` |

## Where to download, and exactly what was used

PatentsView now lives on the USPTO Open Data Portal. The files used for every number in this repository came from the
bulk dataset page `https://data.uspto.gov/bulkdata/datasets/pvgpatdis` (PatentsView granted-patent tables), downloaded as
the `.tsv.zip` versions on **13 Nov 2026**. The portal page is a JavaScript app (no file list for `curl`) and its API needs a
free key, so the download was done in a browser. The files inside the zips are dated 10 to 12 Feb 2026, which is the release.

| File | Zip size (bytes) | Unzipped size (bytes) | Lines | SHA-256 of the unzipped file |
|---|---|---|---|---|
| `g_patent.tsv` | 232,076,712 | 1,122,514,092 | 9,454,162 | `b838d1f337d5a448a046b0eff7d5560e353c2c69f64c3ba1c8cc958be29dadd0` |
| `g_cpc_current.tsv` | 503,091,774 | 3,381,614,094 | | `dec2e7f1b2fe20eac9b6dd655e386456c47b7f1dc81a9cdcab13e7f48d34733b` |
| `g_cpc_title.tsv` | 6,470,929 | 111,393,200 | 271,367 | `2951af19bfb55270ec3134af190397745f283f80dbaac956873f2aa30866b6bd` |
| `g_us_patent_citation.tsv` | 2,253,788,290 | 10,864,139,124 | | `162e5e2d561a8e16b9611117a1d4b0c4d53d7e8a4ee5bccc3aa9517384b01247` |

Check yours with `sha256sum g_*.tsv`. The checksums of the zips themselves were not recorded before the zips were deleted, so
compare the unzipped files and the zip sizes. If PatentsView publishes a newer release, a different file will give different
numbers; the repository's results are for the release above.

The headers of the four files were read and match what the pipeline looks for (checked 13 Nov 2026), so no code change
was needed:

- `g_patent`: `patent_id`, `patent_type`, `patent_date`, `patent_title`, `wipo_kind`, `num_claims`, `withdrawn`, `filename`
- `g_cpc_current`: `patent_id`, `cpc_sequence`, `cpc_section`, `cpc_class`, `cpc_subclass`, `cpc_group`, `cpc_type` (values such as `inventional`)
- `g_cpc_title`: `cpc_subclass`, `cpc_subclass_title`, `cpc_group`, `cpc_group_title`, `cpc_class`, `cpc_class_title`
- `g_us_patent_citation`: `patent_id`, `citation_sequence`, `citation_patent_id`, `citation_date`, `record_name`, `wipo_kind`, `citation_category`

**Where the files were.** The runs reported in the README read the full unzipped files from the repository root (git-ignored). An earlier `data/raw/` folder held the same three tables plus the two-column citation cut below; it was deleted on 14 Nov 2026 after the narrowed-slice run, because everything it held is reproducible from the root copies (`cmp` confirmed they are identical, and the cut is the first and third columns). The pipeline accepts any paths.

**Disk shortcut used for the first run.** On a laptop with 5 to 6 GB free, the 10.9 GB citation file was streamed
out of its zip and cut to the two columns the pipeline uses, so it never sat on disk in full:

```bash
unzip -p g_us_patent_citation.tsv.zip | awk -F'\t' 'BEGIN{OFS="\t"}{print $1,$3}' > data/raw/g_us_patent_citation.tsv
```

The pipeline reads columns by header name. **Checked on 13 Nov 2026:** running the pipeline on the full 10.9 GB citation file
instead gives byte-identical `fields.csv`, `combined_with.csv` and `builds_on.csv`, in 28 seconds with `--memory-limit 3GB`, so
the shortcut is only a disk-space saving, not needed if you have the room. The other three files were used unchanged.

Measured on a 12-core, 15 GB machine: the pipeline took about 25 seconds with `--memory-limit 3GB`.

Notes
- Everything is read as text. Patent ids such as `D345393` or `RE12345` would otherwise be mangled into numbers.
- Only *inventive* classifications are used (`cpc_type` starting with "inv"). If the file has no such column, the
  pipeline warns and uses every code.
- Memory: the citation join is the heavy step. `--memory-limit` and `--temp-dir` are settings; point `--temp-dir` at a disk
  with tens of GB free if you can. With a slice, patents outside the slice drop out before the join. The 25 second figure above was
  measured on the real files.
- **Credit:** the README must credit PatentsView. Check their current licence and attribution wording before submitting.
