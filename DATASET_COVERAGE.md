# Dataset Coverage

Counts are generated from `random_address/addresses-us-all.min.json` on this branch.
Records are kept only when they include `address1`, `city`, `state`, a 5-digit `postalCode`, and coordinates.

- Total addresses: 132,426
- Unique state/DC codes represented: 50
- Unique ZIP codes represented: 26,282
- ZIP codes with at least 5 addresses: 24,459
- ZIP codes with 1-4 addresses: 1,823
- Records with `address2`: 9,720

| State | Name | Original | Net Added | Total | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| AL | Alabama | 193 | 2822 | 3015 | Original plus OpenAddresses/Overture samples |
| AK | Alaska | 174 | 262 | 436 | Original plus OpenAddresses/Overture samples |
| AZ | Arizona | 199 | 1808 | 2007 | Original plus OpenAddresses/Overture samples |
| AR | Arkansas | 190 | 3143 | 3333 | Original plus OpenAddresses/Overture samples |
| CA | California | 332 | 8152 | 8484 | Original plus OpenAddresses/Overture samples |
| CO | Colorado | 230 | 1912 | 2142 | Original plus OpenAddresses/Overture samples |
| CT | Connecticut | 196 | 1393 | 1589 | Original plus OpenAddresses/Overture samples |
| DE | Delaware | 0 | 407 | 407 | Added from OpenAddresses/Overture samples |
| DC | District of Columbia | 196 | 300 | 496 | Original plus OpenAddresses/Overture samples |
| FL | Florida | 208 | 4680 | 4888 | Original plus OpenAddresses/Overture samples |
| GA | Georgia | 192 | 385 | 577 | Original plus OpenAddresses/Overture samples |
| HI | Hawaii | 0 | 42 | 42 | Added from OpenAddresses/Overture samples |
| ID | Idaho | 0 | 475 | 475 | Added from OpenAddresses/Overture samples |
| IL | Illinois | 0 | 6937 | 6937 | Added from OpenAddresses/Overture samples |
| IN | Indiana | 0 | 3952 | 3952 | Added from OpenAddresses/Overture samples |
| IA | Iowa | 0 | 4696 | 4696 | Added from OpenAddresses/Overture samples |
| KS | Kansas | 0 | 3007 | 3007 | Added from OpenAddresses/Overture samples |
| KY | Kentucky | 190 | 3618 | 3808 | Original plus OpenAddresses/Overture samples |
| LA | Louisiana | 0 | 266 | 266 | Added from OpenAddresses/Overture samples |
| ME | Maine | 0 | 2156 | 2156 | Added from OpenAddresses/Overture samples |
| MD | Maryland | 187 | 2227 | 2414 | Original plus OpenAddresses/Overture samples |
| MA | Massachusetts | 188 | 2632 | 2820 | Original plus OpenAddresses/Overture samples |
| MI | Michigan | 0 | 900 | 900 | Added from OpenAddresses/Overture samples |
| MN | Minnesota | 0 | 4206 | 4206 | Added from OpenAddresses/Overture samples |
| MS | Mississippi | 0 | 1733 | 1733 | Added from OpenAddresses/Overture samples |
| MO | Missouri | 0 | 2002 | 2002 | Added from OpenAddresses/Overture samples |
| MT | Montana | 0 | 1858 | 1858 | Added from OpenAddresses/Overture samples |
| NE | Nebraska | 0 | 780 | 780 | Added from OpenAddresses/Overture samples |
| NV | Nevada | 0 | 63 | 63 | Added from OpenAddresses/Overture samples |
| NH | New Hampshire | 0 | 0 | 0 | Not represented by the current complete-record sources |
| NJ | New Jersey | 0 | 3013 | 3013 | Added from OpenAddresses/Overture samples |
| NM | New Mexico | 0 | 1692 | 1692 | Added from OpenAddresses/Overture samples |
| NY | New York | 0 | 8650 | 8650 | Added from OpenAddresses/Overture samples |
| NC | North Carolina | 0 | 3962 | 3962 | Added from OpenAddresses/Overture samples |
| ND | North Dakota | 0 | 2018 | 2018 | Added from OpenAddresses/Overture samples |
| OH | Ohio | 0 | 6022 | 6022 | Added from OpenAddresses/Overture samples |
| OK | Oklahoma | 175 | 2926 | 3101 | Original plus OpenAddresses/Overture samples |
| OR | Oregon | 0 | 2973 | 2973 | Added from OpenAddresses/Overture samples |
| PA | Pennsylvania | 0 | 1606 | 1606 | Added from OpenAddresses/Overture samples |
| RI | Rhode Island | 0 | 145 | 145 | Added from OpenAddresses/Overture samples |
| SC | South Carolina | 0 | 218 | 218 | Added from OpenAddresses/Overture samples |
| SD | South Dakota | 0 | 188 | 188 | Added from OpenAddresses/Overture samples |
| TN | Tennessee | 195 | 3630 | 3825 | Original plus OpenAddresses/Overture samples |
| TX | Texas | 0 | 8119 | 8119 | Added from OpenAddresses/Overture samples |
| UT | Utah | 0 | 1568 | 1568 | Added from OpenAddresses/Overture samples |
| VT | Vermont | 175 | 1289 | 1464 | Original plus OpenAddresses/Overture samples |
| VA | Virginia | 50 | 4412 | 4462 | Original plus OpenAddresses/Overture samples |
| WA | Washington | 0 | 2834 | 2834 | Added from OpenAddresses/Overture samples |
| WV | West Virginia | 0 | 3698 | 3698 | Added from OpenAddresses/Overture samples |
| WI | Wisconsin | 0 | 2988 | 2988 | Added from OpenAddresses/Overture samples |
| WY | Wyoming | 0 | 391 | 391 | Added from OpenAddresses/Overture samples |

| **Total** |  | **3270** | **129156** | **132426** |  |

New Hampshire remains omitted because the checked complete-record sources did not provide usable ZIP-coded address points for this branch.
