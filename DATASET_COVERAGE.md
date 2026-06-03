# Dataset Coverage

Counts are generated from `random_address/addresses-us-all.min.json.gz` on this branch.
Records are kept only when they include `address1`, `city`, `state`, a 5-digit `postalCode`, and coordinates.

- Total addresses: 1,031,008
- Unique state/DC codes represented: 51
- Unique ZIP codes represented: 26,506
- ZIP codes with at least 35 addresses: 23,326
- ZIP codes with at least 25 addresses: 23,683
- ZIP codes with at least 10 addresses: 24,394
- ZIP codes with at least 5 addresses: 24,724
- ZIP codes with 1-4 addresses: 1,782
- Records with `address2`: 110,402
- Precomputed ZIP clusters: 23,340

| State | Name | Main Branch | Added In This PR | Total | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| AK | Alaska | 687 | 1634 | 2321 | Expanded from Overture clustered 35-per-ZIP refresh |
| AL | Alabama | 5271 | 15459 | 20730 | Expanded from Overture clustered 35-per-ZIP refresh |
| AR | Arkansas | 6289 | 18635 | 24924 | Expanded from Overture clustered 35-per-ZIP refresh |
| AZ | Arizona | 3769 | 11536 | 15305 | Expanded from Overture clustered 35-per-ZIP refresh |
| CA | California | 16232 | 49944 | 66176 | Expanded from Overture clustered 35-per-ZIP refresh |
| CO | Colorado | 3989 | 11758 | 15747 | Expanded from Overture clustered 35-per-ZIP refresh |
| CT | Connecticut | 2979 | 9169 | 12148 | Expanded from Overture clustered 35-per-ZIP refresh |
| DC | District of Columbia | 656 | 917 | 1573 | Expanded from Overture clustered 35-per-ZIP refresh |
| DE | Delaware | 736 | 2151 | 2887 | Expanded from Overture clustered 35-per-ZIP refresh |
| FL | Florida | 9489 | 30549 | 40038 | Expanded from Overture clustered 35-per-ZIP refresh |
| GA | Georgia | 898 | 2041 | 2939 | Expanded from Overture clustered 35-per-ZIP refresh |
| HI | Hawaii | 42 | 0 | 42 | No new complete Overture records in this refresh |
| IA | Iowa | 8842 | 25619 | 34461 | Expanded from Overture clustered 35-per-ZIP refresh |
| ID | Idaho | 866 | 2370 | 3236 | Expanded from Overture clustered 35-per-ZIP refresh |
| IL | Illinois | 13685 | 43129 | 56814 | Expanded from Overture clustered 35-per-ZIP refresh |
| IN | Indiana | 7822 | 24925 | 32747 | Expanded from Overture clustered 35-per-ZIP refresh |
| KS | Kansas | 5919 | 18024 | 23943 | Expanded from Overture clustered 35-per-ZIP refresh |
| KY | Kentucky | 7160 | 21312 | 28472 | Expanded from Overture clustered 35-per-ZIP refresh |
| LA | Louisiana | 466 | 1327 | 1793 | Expanded from Overture clustered 35-per-ZIP refresh |
| MA | Massachusetts | 5447 | 17105 | 22552 | Expanded from Overture clustered 35-per-ZIP refresh |
| MD | Maryland | 4604 | 14306 | 18910 | Expanded from Overture clustered 35-per-ZIP refresh |
| ME | Maine | 4245 | 13762 | 18007 | Expanded from Overture clustered 35-per-ZIP refresh |
| MI | Michigan | 1639 | 4804 | 6443 | Expanded from Overture clustered 35-per-ZIP refresh |
| MN | Minnesota | 8222 | 25707 | 33929 | Expanded from Overture clustered 35-per-ZIP refresh |
| MO | Missouri | 3828 | 11623 | 15451 | Expanded from Overture clustered 35-per-ZIP refresh |
| MS | Mississippi | 3355 | 9760 | 13115 | Expanded from Overture clustered 35-per-ZIP refresh |
| MT | Montana | 3689 | 11588 | 15277 | Expanded from Overture clustered 35-per-ZIP refresh |
| NC | North Carolina | 7810 | 25972 | 33782 | Expanded from Overture clustered 35-per-ZIP refresh |
| ND | North Dakota | 3963 | 12014 | 15977 | Expanded from Overture clustered 35-per-ZIP refresh |
| NE | Nebraska | 1457 | 3926 | 5383 | Expanded from Overture clustered 35-per-ZIP refresh |
| NH | New Hampshire | 0 | 2206 | 2206 | Existing branch records retained |
| NJ | New Jersey | 5926 | 18730 | 24656 | Expanded from Overture clustered 35-per-ZIP refresh |
| NM | New Mexico | 3231 | 9481 | 12712 | Expanded from Overture clustered 35-per-ZIP refresh |
| NV | Nevada | 63 | 0 | 63 | No new complete Overture records in this refresh |
| NY | New York | 17078 | 54276 | 71354 | Expanded from Overture clustered 35-per-ZIP refresh |
| OH | Ohio | 11907 | 37998 | 49905 | Expanded from Overture clustered 35-per-ZIP refresh |
| OK | Oklahoma | 5804 | 17294 | 23098 | Expanded from Overture clustered 35-per-ZIP refresh |
| OR | Oregon | 4315 | 11924 | 16239 | Expanded from Overture clustered 35-per-ZIP refresh |
| PA | Pennsylvania | 3053 | 8737 | 11790 | Expanded from Overture clustered 35-per-ZIP refresh |
| RI | Rhode Island | 267 | 768 | 1035 | Expanded from Overture clustered 35-per-ZIP refresh |
| SC | South Carolina | 338 | 824 | 1162 | Expanded from Overture clustered 35-per-ZIP refresh |
| SD | South Dakota | 298 | 605 | 903 | Expanded from Overture clustered 35-per-ZIP refresh |
| TN | Tennessee | 6945 | 20565 | 27510 | Expanded from Overture clustered 35-per-ZIP refresh |
| TX | Texas | 15724 | 47810 | 63534 | Expanded from Overture clustered 35-per-ZIP refresh |
| UT | Utah | 3063 | 9636 | 12699 | Expanded from Overture clustered 35-per-ZIP refresh |
| VA | Virginia | 8840 | 29114 | 37954 | Expanded from Overture clustered 35-per-ZIP refresh |
| VT | Vermont | 2758 | 8592 | 11350 | Expanded from Overture clustered 35-per-ZIP refresh |
| WA | Washington | 5296 | 16162 | 21458 | Expanded from Overture clustered 35-per-ZIP refresh |
| WI | Wisconsin | 5831 | 17859 | 23690 | Expanded from Overture clustered 35-per-ZIP refresh |
| WV | West Virginia | 7269 | 23005 | 30274 | Expanded from Overture clustered 35-per-ZIP refresh |
| WY | Wyoming | 659 | 1635 | 2294 | Expanded from Overture clustered 35-per-ZIP refresh |

| **Total** |  | **252721** | **778287** | **1031008** |  |
