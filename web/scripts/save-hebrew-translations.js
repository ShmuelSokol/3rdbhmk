#!/usr/bin/env node
/**
 * Update translations for pages 14-15 with actual Hebrew characters (ArtScroll style)
 */

const BASE = 'https://3rdbhmk.ksavyad.com';

async function update(pageId, regionId, translatedText) {
  const res = await fetch(`${BASE}/api/pages/${pageId}/pipeline/regions`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ regionId, translatedText })
  });
  if (!res.ok) {
    const d = await res.json();
    console.log('FAIL', regionId, d);
  } else {
    console.log('OK', regionId);
  }
}

async function main() {
  const p14 = 'cmmno2m5c000di9xoxkdnz4on';

  // Region 0: header
  await update(p14, 'cmmwnvsw800ch144f4uypwhur',
    'Introduction \u2014 Summary of the History of the Mishkan and the Mikdash');

  // Region 2: subheader
  await update(p14, 'cmmwnvtv500cl144frcm7zv1g', 'The Mishkan in Shiloh');

  // Region 3: main body \u2014 ArtScroll style WITH Hebrew characters
  await update(p14, 'cmmwnvubq00cn144fq3iarmby',
`The Mishnah (Zevachim 14:6) teaches:

\u05D1\u05D0\u05D5 \u05DC\u05E9\u05D9\u05DC\u05D4 \u2014 They came to Shiloh. As it is written (Yehoshua 18:1): \u05D5\u05D9\u05E7\u05D4\u05DC\u05D5 \u05DB\u05DC \u05E2\u05D3\u05EA \u05D1\u05E0\u05D9 \u05D9\u05E9\u05E8\u05D0\u05DC \u05E9\u05D9\u05DC\u05D4 \u05D5\u05D9\u05E9\u05DB\u05D9\u05E0\u05D5 \u05E9\u05DD \u05D0\u05EA \u05D0\u05D4\u05DC \u05DE\u05D5\u05E2\u05D3 \u2014 The entire assembly of Bnei Yisrael gathered at Shiloh and they established there the Ohel Mo\u2019ed. They placed there the Mizbe\u2019ach and the Aron.

\u05E0\u05D0\u05E1\u05E8\u05D5 \u05D4\u05D1\u05DE\u05D5\u05EA \u2014 The bamos were forbidden: It was prohibited to bring korbanos on private bamos; rather, one had to bring and offer in the Ohel Mo\u2019ed.

\u05DC\u05D0 \u05D4\u05D9\u05D4 \u05E9\u05DD \u05EA\u05E7\u05E8\u05D4 \u05D0\u05DC\u05D0 \u05D1\u05D9\u05EA \u05E9\u05DC \u05D0\u05D1\u05E0\u05D9\u05DD \u05DE\u05DC\u05DE\u05D8\u05DF \u05D5\u05D9\u05E8\u05D9\u05E2\u05D5\u05EA \u05DE\u05DC\u05DE\u05E2\u05DC\u05DF \u2014 There was no ceiling there, but rather a house of stones below and curtains above: The Mishkan in Shiloh was not constructed of the kerashim (wooden planks) used in the Midbar, but rather it was a structure of stones without a ceiling, with the yeri\u2019os (curtains) of the Mishkan spread above in place of the ceiling. From here it was called a \u201Cbayis\u201D (house), as it is written (Shmuel I 1:24): \u05D5\u05EA\u05D1\u05D9\u05D0\u05D4\u05D5 \u05D1\u05D9\u05EA \u05D4\u2019 \u05E9\u05D9\u05DC\u05D4 \u2014 She brought him to the House of Hashem in Shiloh. And it was also called a \u201CMishkan,\u201D as it is written (Tehillim 78:60): \u05D5\u05D9\u05D8\u05E9 \u05DE\u05E9\u05DB\u05DF \u05E9\u05D9\u05DC\u05D4 \u2014 He abandoned the Mishkan of Shiloh.

\u05D5\u05D4\u05D9\u05D0 \u05D4\u05D9\u05EA\u05D4 \u05DE\u05E0\u05D5\u05D7\u05D4 \u2014 And it was the menuchah: As it is written (Devarim 12:9): \u05DB\u05D9 \u05DC\u05D0 \u05D1\u05D0\u05EA\u05DD \u05E2\u05D3 \u05E2\u05EA\u05D4 \u05D0\u05DC \u05D4\u05DE\u05E0\u05D5\u05D7\u05D4 \u2014 For you have not yet come to the rest. The meaning is: when you cross the Yarden (ibid. 11:31), you are permitted to offer on bamos until you come to the menuchah. Chazal expounded: \u05DE\u05E0\u05D5\u05D7\u05D4 \u2014 this is Shiloh, for they rested there after fourteen years of kibush v\u2019chiluk (conquest and division of Eretz Yisrael). Therefore, when they came to Shiloh, the bamos were forbidden.

\u05E7\u05D3\u05E9\u05D9 \u05E7\u05D3\u05E9\u05D9\u05DD \u05E0\u05D0\u05DB\u05DC\u05D9\u05DD \u05DC\u05E4\u05E0\u05D9\u05DD \u05DE\u05DF \u05D4\u05E7\u05DC\u05E2\u05D9\u05DD \u2014 Kodshei kodashim are eaten within the curtains \u2014 that is, within the walls of the Beis Hashem in Shiloh.

\u05E7\u05D3\u05E9\u05D9\u05DD \u05E7\u05DC\u05D9\u05DD \u05D5\u05DE\u05E2\u05E9\u05E8 \u05E9\u05E0\u05D9 \u2014 Kodashim kalim and ma\u2019aser sheini \u2014 for they became obligated in ma\u2019aser sheini after they conquered and divided Eretz Yisrael.

\u05D1\u05DB\u05DC \u05D4\u05E8\u05D5\u05D0\u05D4 \u2014 Anywhere within sight: One may eat them in any place from which Shiloh can be seen (Rashi). Others explain: in any place from which one can see some portion of the Beis Hashem (Rambam).

Chazal derived this halachah from the pasuk (Devarim 12:13): \u05D4\u05E9\u05DE\u05E8 \u05DC\u05DA \u05E4\u05DF \u05EA\u05E2\u05DC\u05D4 \u05E2\u05DC\u05EA\u05D9\u05DA \u05D1\u05DB\u05DC \u05DE\u05E7\u05D5\u05DD \u05D0\u05E9\u05E8 \u05EA\u05E8\u05D0\u05D4 \u2014 Beware lest you offer your olos in any place that you see \u2014 in any place that you see, you may not offer, but you may eat in any place that you see (mefarshim).

The Mishkan in Shiloh was built in the year 2928 from the creation of the world (Seder HaDoros HaKatzar, Rav Benizri).`);

  // Region 4: footer
  await update(p14, 'cmmwnvusf00cp144fkabw1ca8',
    'The Mishkan stood in Shiloh for 369 years (Zevachim 118b).');

  console.log('Page 14 done with Hebrew');

  // ─── Page 15 ───
  const p15 = 'cmmno2m5c000ei9xo5s4pdz4o';

  await update(p15, 'cmmwnw6ge00cx144fcmw8f3tb',
`The Mishnah (Zevachim 14:7) teaches:

\u05D5\u05DC\u05D2\u05D1\u05E2\u05D5\u05DF \u2014 And to Giv\u2019on: After Nov was destroyed in the days of Shaul HaMelech (Shmuel I, perakim 21-22), they transferred the Mishkan to Giv\u2019on, as it is written (Melachim I 3:4): \u05D5\u05D9\u05DC\u05DA \u05D4\u05DE\u05DC\u05DA \u05D2\u05D1\u05E2\u05D5\u05E0\u05D4 \u05DC\u05D6\u05D1\u05D7 \u05E9\u05DD \u05DB\u05D9 \u05D4\u05D9\u05D0 \u05D4\u05D1\u05DE\u05D4 \u05D4\u05D2\u05D3\u05D5\u05DC\u05D4 \u2014 The king went to Giv\u2019on to bring korbanos there, for that was the great bamah. The Mishkan stood there for forty-four years.

During that period of Nov and Giv\u2019on, the bamos were again permitted. As it is written (Devarim 12:9): \u05DB\u05D9 \u05DC\u05D0 \u05D1\u05D0\u05EA\u05DD \u05E2\u05D3 \u05E2\u05EA\u05D4 \u05D0\u05DC \u05D4\u05DE\u05E0\u05D5\u05D7\u05D4 \u05D5\u05D0\u05DC \u05D4\u05E0\u05D7\u05DC\u05D4 \u2014 For you have not yet come to the rest and to the inheritance. Chazal expounded: \u05DE\u05E0\u05D5\u05D7\u05D4 \u2014 this is Shiloh (as explained in the previous Mishnah); \u05E0\u05D7\u05DC\u05D4 \u2014 this is Yerushalayim (as explained in the following Mishnah). That is, when they come to Shiloh and to Yerushalayim, the bamos will be forbidden. Why did the pasuk divide them? To allow a period of heter (permission) between the two (Gemara) \u2014 meaning that after the period of \u201Cmenuchah\u201D (Shiloh), the bamos once again became permitted until they would come \u201Cto the nachalah\u201D and build the Beis HaMikdash in Yerushalayim.

\u05E7\u05D3\u05E9\u05D9 \u05E7\u05D3\u05E9\u05D9\u05DD \u05E0\u05D0\u05DB\u05DC\u05D9\u05DD \u05DC\u05E4\u05E0\u05D9\u05DD \u05DE\u05DF \u05D4\u05E7\u05DC\u05E2\u05D9\u05DD \u2014 Kodshei kodashim are eaten within the curtains of the Mishkan, for they may only be offered on the bamah gedolah.

\u05E7\u05D3\u05E9\u05D9\u05DD \u05E7\u05DC\u05D9\u05DD \u05D1\u05DB\u05DC \u05E2\u05E8\u05D9 \u05D9\u05E9\u05E8\u05D0\u05DC \u2014 Kodashim kalim may be offered in all the cities of Yisrael: Wherever it may be, one was permitted to build a bamah and offer kodashim kalim upon it. The same applied to ma\u2019aser sheini, which was permitted to be eaten anywhere, for the Torah linked them, as it states (Devarim 12:17): \u05DC\u05D0 \u05EA\u05D5\u05DB\u05DC \u05DC\u05D0\u05DB\u05DC \u05D1\u05E9\u05E2\u05E8\u05D9\u05DA \u05DE\u05E2\u05E9\u05E8 \u05D3\u05D2\u05E0\u05DA \u2014 When kodashim kalim require being brought to a designated place, ma\u2019aser sheini also requires being brought to a designated place; when kodashim kalim may be offered in all the cities of Yisrael, ma\u2019aser sheini may also be eaten in all the cities of Yisrael (Bartenura).

Our Mishnah used the phrase \u201Cin all the cities of Yisrael\u201D because by this period, after the kibush v\u2019chiluk, they had already built cities for themselves. However, in the time of Gilgal they did not yet have established cities, and therefore the earlier Mishnah (14:5) stated: \u05E7\u05D3\u05E9\u05D9\u05DD \u05E7\u05DC\u05D9\u05DD \u05D1\u05DB\u05DC \u05DE\u05E7\u05D5\u05DD \u2014 kodashim kalim in any place (Rambam).`);

  console.log('Page 15 done with Hebrew');
}

main().catch(e => { console.error(e); process.exit(1); });
