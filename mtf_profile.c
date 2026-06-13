#include "bzlib_private.h"

static
void record_mtf_position ( EState* s, Int32 position )
{
   Int32 bucket;
   UInt32 oldTotal;

   if (position < 16) bucket = position;
   else if (position < 32) bucket = 16;
   else if (position < 64) bucket = 17;
   else if (position < 128) bucket = 18;
   else bucket = 19;
   s->profileMTFPositions[bucket]++;
   oldTotal = s->profileMTFTotalLo;
   s->profileMTFTotalLo++;
   if (s->profileMTFTotalLo < oldTotal) s->profileMTFTotalHi++;
}

void BZ2_generateMTFValuesProfile ( EState* s )
{
   UChar yy[256];
   Int32 i, j;
   Int32 zPend;
   Int32 wr;
   Int32 EOB;
   UInt32* ptr = s->ptr;
   UChar* block = s->block;
   UInt16* mtfv = s->mtfv;

   s->nInUse = 0;
   for (i = 0; i < 256; i++)
      if (s->inUse[i]) {
         s->unseqToSeq[i] = (UChar)s->nInUse;
         s->nInUse++;
      }
   EOB = s->nInUse + 1;
   for (i = 0; i <= EOB; i++) s->mtfFreq[i] = 0;
   wr = 0;
   zPend = 0;
   for (i = 0; i < s->nInUse; i++) yy[i] = (UChar)i;

   for (i = 0; i < s->nblock; i++) {
      UChar ll_i;
      if (s->blockIsBWT) {
         ll_i = s->unseqToSeq[s->bwt[i]];
      } else {
         j = ptr[i] - 1;
         if (j < 0) j += s->nblock;
         ll_i = s->unseqToSeq[block[j]];
      }

      if (yy[0] == ll_i) {
         record_mtf_position ( s, 0 );
         zPend++;
      } else {
         if (zPend > 0) {
            zPend--;
            while (True) {
               UInt16 runSymbol = (zPend & 1) ? BZ_RUNB : BZ_RUNA;
               mtfv[wr++] = runSymbol;
               s->mtfFreq[runSymbol]++;
               if (zPend < 2) break;
               zPend = (zPend - 2) / 2;
            }
            zPend = 0;
         }
         {
            UChar rtmp;
            UChar* ryy_j;
            rtmp = yy[1];
            yy[1] = yy[0];
            ryy_j = &(yy[1]);
            while (ll_i != rtmp) {
               UChar rtmp2;
               ryy_j++;
               rtmp2 = rtmp;
               rtmp = *ryy_j;
               *ryy_j = rtmp2;
            }
            yy[0] = rtmp;
            j = (Int32)(ryy_j - &(yy[0]));
            record_mtf_position ( s, j );
            mtfv[wr++] = (UInt16)(j + 1);
            s->mtfFreq[j + 1]++;
         }
      }
   }

   if (zPend > 0) {
      zPend--;
      while (True) {
         UInt16 runSymbol = (zPend & 1) ? BZ_RUNB : BZ_RUNA;
         mtfv[wr++] = runSymbol;
         s->mtfFreq[runSymbol]++;
         if (zPend < 2) break;
         zPend = (zPend - 2) / 2;
      }
   }
   mtfv[wr++] = (UInt16)EOB;
   s->mtfFreq[EOB]++;
   s->nMTF = wr;
}
