#!/usr/bin/env node
/**
 * Save ArtScroll-style translations for sample pages 25 (null regions)
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
  const p25 = 'cmmno2m5c000oi9xoqbh5fr64';

  // Region 16 (table): Har HaBayis description
  await update(p25, 'cmmwo1rou00jz144fwrw8ueuj',
    '[19] Har HaBayis: Har HaBayis has a wall surrounding it entirely, five hundred kanim long by five hundred kanim wide, which equals three thousand amos by three thousand amos (below, Perek 42, pesukim 16-20).');

  // Region 17 (table): Metzudas Dovid etc.
  await update(p25, 'cmmwo1s5x00k1144f522lxwr2',
    "This is also the opinion of the Metzudas Dovid, the Malbim, and Binyan HaBayis (by HaRav HaGaon Yechiel Hillel, based on Metzudas Dovid) \u2014 that all four walls of Har HaBayis are low. Similarly, the Radak implies this when he wrote: \u201CIn the second Beis HaMikdash they made the eastern wall low as they saw in Yechezkel\u2019s future building, and they adopted some features of the Third Beis HaMikdash but not everything.\u201D");

  // Region 18 (table): Mishkenos Elyon quote
  await update(p25, 'cmmwo1smx00k3144fxwghj66j',
    'Similarly, it is written in Mishkenos Elyon (folio 196, Chapter 1), Mishnah 1: "Har HaBayis is three thousand amos by three thousand amos. Its largest portion is to the south, its second portion to the east, its third portion to the north, its smallest portion to the west. The place where its measurement is greatest, there its primary use is" [Diagram H-3].');

  // Region 19 (table): Height and width of openings
  await update(p25, 'cmmwo1t3y00k5144f4xtw99mv',
    'Height and width of the openings: The Navi does not mention the height and width of the openings. In Mishkenos Elyon (folio 170) it states: "The height of all openings, apart from the inner opening [of the Kodesh HaKodashim], are as high as is appropriate. Fifty amos is the height of the opening, for thus all the arrangements were divided for the neshamos..."');

  // Region 20 (table): Explanation of BHM location
  await update(p25, 'cmmwo1tl000k7144f6b83mqxf',
    'Explanation: The site of the Beis HaMikdash is close to the northwest of Har HaBayis. Therefore, the largest open area is to the south, then to the east, less available space to the north, and the least available space to the west.');

  // Region 21 (table): Gates and measurements
  await update(p25, 'cmmwo1u2100k9144flqjf031q',
    'The gates of Har HaBayis are not mentioned by the Navi. In Mishkenos Elyon, Mishnah 2, it states: "It shall have five gates: two to the south, one to the east, one to the north, and one to the west." This was also the arrangement in the Second Beis HaMikdash (Mishnah Middos 1:3) [Diagram H-3]. The height of the openings is fifty amos, and their width ten amos. The thickness of the opening corresponds to the thickness of the wall [Diagram H-4].');

  // Region 22 (table): Measurements diagram labels
  await update(p25, 'cmmwo1uj100kb144f140l5b8g',
    '10 amos | 10 amos | 10 amos | 60 amos | 50 amos | 6 amos | 10 amos');

  // Region 23 (table): Wall height
  await update(p25, 'cmmwo1v0200kd144fnawjxbak',
    'Height of the wall of Har HaBayis: In Mishkenos Elyon, Mishnah 2, it states: "The height of the wall is six [amos] and its thickness six" \u2014 in all four directions: north, south, east, and west.');

  // Region 24 (table): Rashi's opinion
  await update(p25, 'cmmwo1vh400kf144ft0qk7nbh',
    "This is the opinion of Rashi, who wrote: \u201CThis is the outer structure that surrounds Har HaBayis, and it was low, as we learned (Middos 2:4): 'Kol ha\u2019kesalim she\u2019hayu sham hayu gevohim, chutz mi\u2019kosel mizrachi' \u2014 All the walls that were there were high, except for the eastern wall, etc.\u201D\n\nRashi does not mean that only one wall will be low in the Third Beis HaMikdash. Rather, just as in the Second Beis HaMikdash one wall was low, so too in the Third Beis HaMikdash all four walls of Har HaBayis will be low \u2014 only six amos. Perhaps this is for the beauty of the Bayis, that the wall of Har HaBayis appears low from the outside [Diagram H-3].");

  // Region 25 (table): Diagram label
  await update(p25, 'cmmwo1vzk00kh144f2uenouwv',
    '6 amos \u2014 Diagram H-4: Gate of the Wall of Har HaBayis');

  // Region 26 (header): Hashlamas Saras
  await update(p25, 'cmmwo1wgl00kj144fcrridjje', 'Hashlamas Saras');

  // Region 27 (table): About amah measurements
  await update(p25, 'cmmwo1wxm00kl144f7qk04e63',
    "Except for the golden Mizbe\u2019ach, and the keren and the yesod [and the keilim]. R\u2019 Yehudah says: The amah of the building is six tefachim and that of the keilim is five tefachim. The Gemara in Menachos (97a) explains that the source for the opinions of R\u2019 Meir and R\u2019 Yehudah is from the Navi Yechezkel (Perek 43, pasuk 13) [and so it is in Eruvin (4a) and in Sukkah (5b)].");

  // Region 28 (table): Rambam ruling
  await update(p25, 'cmmwo1xep00kn144ff3zioocm',
    "The Rambam in Hilchos Beis HaBechirah (Perek 2, Halachah 6-7) ruled in accordance with R\u2019 Meir [although the notation in the Gemara in Ayin Mishpat points to R\u2019 Yehudah, and Maran in the Kesef Mishnah wrote that the Rambam\u2019s source is from Maseches Keilim according to R\u2019 Yehudah, nevertheless the Kesef Mishnah continues that the Rambam\u2019s words are in accordance with R\u2019 Meir in Menachos (97a-98a). And the Rambam in Hilchos Me\u2019ilah (Perek 8, Halachah 5) cited the Gemara in Menachos (98a) that the craftsmen add to the building more than they were obligated, so that they should not come to benefit from hekdesh. And the Kesef Mishnah there wrote: \u201COne should wonder why Rabbeinu omitted the law of the keilim that are of silver and gold.\u201D It emerges that according to the Kesef Mishnah, the halachah follows R\u2019 Meir that the measurement of the keilim is according to the standard amah. And so ruled R\u2019 Ovadiah mi\u2019Bartenura in the Mishnah in Keilim (Perek 17, Mishnah 9) that the halachah follows R\u2019 Meir.");

  // Region 29 (table): Rambam ruling continued — same content as 28's continuation
  await update(p25, 'cmmwo1xvr00kp144fpr5cw595',
    "The Rambam in Hilchos Beis HaBechirah (Perek 2, Halachos 6-7) ruled according to R\u2019 Meir. Although the Gemara\u2019s Ayin Mishpat references R\u2019 Yehudah, and the Kesef Mishnah initially identifies the Rambam\u2019s source as Maseches Keilim following R\u2019 Yehudah, the Kesef Mishnah ultimately concludes that the Rambam\u2019s ruling accords with R\u2019 Meir in Menachos (97a-98a). The Rambam in Hilchos Me\u2019ilah (Perek 8, Halachah 5) cites the principle that craftsmen add to the building beyond their obligation to avoid deriving benefit from hekdesh.");

  // Region 30 (table): Chazon Ish measurements
  await update(p25, 'cmmwo1yct00kr144fof6hob44',
    'According to the Chazon Ish, the measurement of a tefach is 9.6 cm, and according to R\u2019 Chaim Na\u2019eh it is 8 cm. In Mishkenos Elyon (folio 178) it states: "The tefach is four etzba\u2019os, and it is five. And both things are true, for its secret is the four letters of the Name, blessed be He, and when you count the kotz (crown) with them, they are five."');

  console.log('\nPage 25 done \u2014 all 15 null regions translated');
}

main().catch(e => { console.error(e); process.exit(1); });
