# Location data review

The source review found no missing French or Arabic governorate or admin3
names at the time the static seed was generated. Names that cannot be verified
in the source are left blank rather than invented; the generated review file is:

- `backend/data/location/location-review.csv`

The synthetic fallback name is `Autre / zone rurale` with the Arabic label
`أخرى / منطقة ريفية`, and is included once for every governorate.
