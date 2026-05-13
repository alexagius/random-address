# Dataset Coverage

Counts are generated from `random_address/addresses-us-all.min.json` on this branch.
Records are kept only when they include `address1`, `city`, `state`, a 5-digit `postalCode`, and coordinates.

- Total addresses: 252,721
- Unique state/DC codes represented: 50
- Unique ZIP codes represented: 26,282
- ZIP codes with at least 10 addresses: 24,063
- ZIP codes with at least 5 addresses: 24,496
- ZIP codes with 1-4 addresses: 1,786
- Records with `address2`: 18,384

| State | Name | Main Branch | Added In This PR | Total | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| AL | Alabama | 3015 | 2256 | 5271 | Expanded by Overture 10-per-ZIP sampling |
| AK | Alaska | 436 | 251 | 687 | Expanded by Overture 10-per-ZIP sampling |
| AZ | Arizona | 2007 | 1762 | 3769 | Expanded by Overture 10-per-ZIP sampling |
| AR | Arkansas | 3333 | 2956 | 6289 | Expanded by Overture 10-per-ZIP sampling |
| CA | California | 8484 | 7748 | 16232 | Expanded by Overture 10-per-ZIP sampling |
| CO | Colorado | 2142 | 1847 | 3989 | Expanded by Overture 10-per-ZIP sampling |
| CT | Connecticut | 1589 | 1390 | 2979 | Expanded by Overture 10-per-ZIP sampling |
| DE | Delaware | 407 | 329 | 736 | Expanded by Overture 10-per-ZIP sampling |
| DC | District of Columbia | 496 | 160 | 656 | Expanded by Overture 10-per-ZIP sampling |
| FL | Florida | 4888 | 4601 | 9489 | Expanded by Overture 10-per-ZIP sampling |
| GA | Georgia | 577 | 321 | 898 | Expanded by Overture 10-per-ZIP sampling |
| HI | Hawaii | 42 | 0 | 42 | Unchanged from main |
| ID | Idaho | 475 | 391 | 866 | Expanded by Overture 10-per-ZIP sampling |
| IL | Illinois | 6937 | 6748 | 13685 | Expanded by Overture 10-per-ZIP sampling |
| IN | Indiana | 3952 | 3870 | 7822 | Expanded by Overture 10-per-ZIP sampling |
| IA | Iowa | 4696 | 4146 | 8842 | Expanded by Overture 10-per-ZIP sampling |
| KS | Kansas | 3007 | 2912 | 5919 | Expanded by Overture 10-per-ZIP sampling |
| KY | Kentucky | 3808 | 3352 | 7160 | Expanded by Overture 10-per-ZIP sampling |
| LA | Louisiana | 266 | 200 | 466 | Expanded by Overture 10-per-ZIP sampling |
| ME | Maine | 2156 | 2089 | 4245 | Expanded by Overture 10-per-ZIP sampling |
| MD | Maryland | 2414 | 2190 | 4604 | Expanded by Overture 10-per-ZIP sampling |
| MA | Massachusetts | 2820 | 2627 | 5447 | Expanded by Overture 10-per-ZIP sampling |
| MI | Michigan | 900 | 739 | 1639 | Expanded by Overture 10-per-ZIP sampling |
| MN | Minnesota | 4206 | 4016 | 8222 | Expanded by Overture 10-per-ZIP sampling |
| MS | Mississippi | 1733 | 1622 | 3355 | Expanded by Overture 10-per-ZIP sampling |
| MO | Missouri | 2002 | 1826 | 3828 | Expanded by Overture 10-per-ZIP sampling |
| MT | Montana | 1858 | 1831 | 3689 | Expanded by Overture 10-per-ZIP sampling |
| NE | Nebraska | 780 | 677 | 1457 | Expanded by Overture 10-per-ZIP sampling |
| NV | Nevada | 63 | 0 | 63 | Unchanged from main |
| NH | New Hampshire | 0 | 0 | 0 | Not represented by the current complete-record sources |
| NJ | New Jersey | 3013 | 2913 | 5926 | Expanded by Overture 10-per-ZIP sampling |
| NM | New Mexico | 1692 | 1539 | 3231 | Expanded by Overture 10-per-ZIP sampling |
| NY | New York | 8650 | 8428 | 17078 | Expanded by Overture 10-per-ZIP sampling |
| NC | North Carolina | 3962 | 3848 | 7810 | Expanded by Overture 10-per-ZIP sampling |
| ND | North Dakota | 2018 | 1945 | 3963 | Expanded by Overture 10-per-ZIP sampling |
| OH | Ohio | 6022 | 5885 | 11907 | Expanded by Overture 10-per-ZIP sampling |
| OK | Oklahoma | 3101 | 2703 | 5804 | Expanded by Overture 10-per-ZIP sampling |
| OR | Oregon | 2973 | 1342 | 4315 | Expanded by Overture 10-per-ZIP sampling |
| PA | Pennsylvania | 1606 | 1447 | 3053 | Expanded by Overture 10-per-ZIP sampling |
| RI | Rhode Island | 145 | 122 | 267 | Expanded by Overture 10-per-ZIP sampling |
| SC | South Carolina | 218 | 120 | 338 | Expanded by Overture 10-per-ZIP sampling |
| SD | South Dakota | 188 | 110 | 298 | Expanded by Overture 10-per-ZIP sampling |
| TN | Tennessee | 3825 | 3120 | 6945 | Expanded by Overture 10-per-ZIP sampling |
| TX | Texas | 8119 | 7605 | 15724 | Expanded by Overture 10-per-ZIP sampling |
| UT | Utah | 1568 | 1495 | 3063 | Expanded by Overture 10-per-ZIP sampling |
| VT | Vermont | 1464 | 1294 | 2758 | Expanded by Overture 10-per-ZIP sampling |
| VA | Virginia | 4462 | 4378 | 8840 | Expanded by Overture 10-per-ZIP sampling |
| WA | Washington | 2834 | 2462 | 5296 | Expanded by Overture 10-per-ZIP sampling |
| WV | West Virginia | 3698 | 3571 | 7269 | Expanded by Overture 10-per-ZIP sampling |
| WI | Wisconsin | 2988 | 2843 | 5831 | Expanded by Overture 10-per-ZIP sampling |
| WY | Wyoming | 391 | 268 | 659 | Expanded by Overture 10-per-ZIP sampling |

| **Total** |  | **132426** | **120295** | **252721** |  |

New Hampshire remains omitted because the checked complete-record sources did not provide usable ZIP-coded address points for this branch.
