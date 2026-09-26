// ML vs PMV comparison (G-02): both classes are shown side by side, with whether they
// agree. When either side is not a normal-validity result (ML extrapolating or PMV out of
// range), the comparison is flagged as not a normal-validity comparison instead of silently
// agreeing or disagreeing.

import { ML_IN_DOMAIN_STATUS, PMV_VALID } from "./format.js";

export function compareMlPmv(record) {
  const { ml, pmv } = record;
  const pmvResolved = pmv.status === PMV_VALID;
  const mlInDomain = ml.domain_status === ML_IN_DOMAIN_STATUS;
  const agree = pmvResolved ? ml.comfort_class === pmv.comfort_class : null;
  return {
    mlClass: ml.comfort_class,
    pmvClass: pmvResolved ? pmv.comfort_class : null,
    pmvStatus: pmv.status,
    agree,
    // True when the comparison is not between two normal-validity results.
    caveat: !mlInDomain || !pmvResolved,
  };
}
