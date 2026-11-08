# Tunisia location data sources

## Administrative reference data

The static reference data in `backend/data/location/` is derived from the
Humanitarian Data Exchange Tunisia Common Operational Datasets administrative
boundaries package:

- Source: <https://data.humdata.org/dataset/cod-ab-tun>
- Publisher/source dataset: Institut National de la Statistique Tunisie
- Licence: Creative Commons Attribution for Intergovernmental Organisations
  (CC BY-IGO 3.0), as recorded by HDX. See the dataset page for attribution
  terms and the licence text.
- Dataset snapshot used for the seed: 2022-11-15 to 2024-12-19.
- Resource: `tun_admin_boundaries.xlsx`

The governorate layer supplies the 24 governorates and centroids. The admin3
layer supplies delegation/municipality-area choices and bilingual labels.
Slugs are generated locally for stable application identifiers; they are not
source location codes.

## Runtime policy

The application does not fetch location data at runtime. Migrations read the
committed CSV snapshots under `backend/data/location/`.

## Attribution

Use: United Nations Office for the Coordination of Humanitarian Affairs
(OCHA) Tunisia administrative boundary product, based on INS Tunisia source
data. Under CC BY-IGO, include attribution on derivative publications or
maps that display the data.
