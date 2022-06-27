/* Missing data interpolation using t-x-y streaming prediction filter with varying smoothness and noncausal structure. */
/*
  Copyright (C) 2021 Jilin University
  
  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.
  
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*/
#include <rsf.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

int main(int argc, char* argv[])
{
    bool smooth, verb;
    int i1, i2, i3, it, ix, iy, n1, n2, n3, n12, n123;
    int dim, na, i, nst, nsy, seed;
    int a[SF_MAX_DIM], n[SF_MAX_DIM];
    int *mask;
    float dd, da, dn, dea, rn, lambda, lambda1, lambda2, lambda3;
    float var, epst, epsx, epsy;
    float *d, *aa, *st, *sy;

    sf_file in,out,known;

    sf_init(argc,argv);
    
    in = sf_input("in");
    out = sf_output("out");
    
    if (!sf_getbool("verb", &verb)) verb = false;
    if (!sf_getbool("smooth", &smooth))	smooth = true;
    /* If yes, use varying smoothness */
    
    known = sf_input("known");
    if (SF_INT != sf_gettype(known)) sf_error("Need int type in known");

    dim = sf_filedims(in,n);
    if (3 < dim) dim = 3;

    if (!sf_getints("a",a,dim)) sf_error("Need a=");
    
    if (dim < 3) sf_error("Need at least three dimension");
    
    
    n123 = 1;
    na = 1;
    
    for (i=0; i < dim; i++) {
	n123 *= n[i];
	na *= a[i];
    }
    
    n1=n[0];
    n2=n[1];
    n3=n[2];
    n12=n[0]*n[1];
    nst=na*n2;
    nsy=na*n12;
    
    if (!sf_getfloat("epst",&epst)) epst = 0;
    /* Smoothness in t direction */

    if (!sf_getfloat("epsx",&epsx)) epsx = 0;
    /* Smoothness in x direction */
    
    if (!sf_getfloat("epsy",&epsy)) epsy = 0;	
    /* Smoothness in y direction */

    if (!sf_getfloat("lambda1",&lambda1)) sf_error("Need lambda1=");
    /* Regularization in t direction */

    lambda1*=lambda1;

    if (!sf_getfloat("lambda2",&lambda2)) sf_error("Need lambda2=");
    /* Regularization in x direction5 */
    
    lambda2*=lambda2;

     if (!sf_getfloat("lambda3",&lambda3)) sf_error("Need lambda3=");
    /* Regularization in y direction */
     
    lambda3*=lambda3;

    lambda=lambda1+lambda2+lambda3;
     
    if(verb)
	sf_warning("lambda1=%f, lambda2=%f, lambda3=%f, lambda=%f, epst=%f, epsx=%f epsy=%f ", lambda1, lambda2, lambda3, lambda, epst, epsx, epsy);
    
    d = sf_floatalloc(2*n123);
    aa = sf_floatalloc(na);
    st = sf_floatalloc(nst);
    sy = sf_floatalloc(nsy);
    mask = sf_intalloc(2*n123);
    
    if(verb) sf_warning("Open space.");
  
    sf_intread(mask,n123,known);
    sf_floatread(d,n123,in);
    
    if(verb) sf_warning("Read mask and data.");
    
    if (!sf_getfloat("var",&var)) var=0.0f;
    /* noise variance */
    var = sqrtf(var);

    if (!sf_getint("seed",&seed)) seed = time(NULL);
    /* random seed */ 
    init_genrand((unsigned long) seed);

    for (i=0; i< na; i++) {
	aa[i] = 0.0f;
    }
    for (i=0; i< nst; i++) {
	st[i] = 0.0f;
    }
    for (i=0; i< nsy; i++) {
	sy[i] = 0.0f;
    }
    
    if(verb) sf_warning("Initialize filter.");
	
    for (i3=0; i3 < n3; i3++) {
	for (i1=0; i1 < n1; i1++) {
	    for (i2=0; i2 < n2; i2++) {
		dd = 0.0f;
		da = 0.0f;
		dea = 0.0f;
		i=0;
		for (ix=-(a[1]-1)/2; ix < (a[1]+1)/2; ix++) {
		    for (it=-(a[0]-1)/2; it < (a[0]+1)/2; it++)	{
			for (iy=-(a[2]-1)/2; iy < (a[2]+1)/2; iy++) {
			    if(ix!=0 && iy!=0) {
				if(i2+ix-1<0 || i2+ix>n2 || i1+it-1<0 || i1+it>n1 || i3+iy-1<0 || i3+iy>n3) {
				    i++;
				}
				else {
				    dd += d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it]*
					d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it];
				    
				    da += d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it]*
					(lambda2*aa[i]+lambda1*st[i2*na+i]+lambda3*sy[i1*n2*na+i2*na+i])/lambda;
				    
				    if(smooth) {
					dea += d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it]*(lambda2*aa[i]*(1+epsx*(-d[(i3+iy)*(n1*n2)+(i2+ix-1)*n1+i1+it]+d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it]))+lambda1*st[i2*na+i]*(1+epst*(-d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it-1]+d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it]))+lambda3*sy[i1*n2*na+i2*na+i]*(1+epsy*(-d[(i3+iy-1)*(n1*n2)+(i2+ix)*n1+i1+it]+d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it])))/lambda;
				    }
				    else {
					dea += d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it]*(lambda2*aa[i]+lambda1*st[i2*na+i]+lambda3*sy[i1*n2*na+i2*na+i])/lambda;
				    }
				    i++;
				}
			    }
			}
		    }
		}
			
		if(mask[i3*n1*n2+i2*n1+i1]) {
		    dn = d[i3*n1*n2+i2*n1+i1];
		    rn = (-dn + dea) / (lambda + dd);
		}
		else {
		    rn = var * sf_randn_one_bm() / lambda;
		    dn = rn*(lambda+dd)+da;
		    d[i3*n1*n2+i2*n1+i1] = dn;
		}
		
		i=0;
		for (ix=-(a[1]-1)/2; ix < (a[1]+1)/2; ix++) {
		    for (it=-(a[0]-1)/2; it < (a[0]+1)/2; it++)	{
			for (iy=-(a[2]-1)/2; iy < (a[2]+1)/2; iy++) {
			    if(ix!=0 && iy!=0) {
				if(i2+ix-1<0 || i2+ix>n2 || i1+it-1<0 || i1+it>n1 || i3+iy-1<0 || i3+iy>n3) {
				    i++;
				}
				else {
				    if(smooth) {
					aa[i] = (lambda2*aa[i]*(1+epsx*(-d[(i3+iy)*(n1*n2)+(i2+ix-1)*n1+i1+it]+d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it]))+lambda1*st[i2*na+i]*(1+epst*(-d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it-1]+d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it]))+lambda3*sy[i1*n2*na+i2*na+i]*(1+epsy*(-d[(i3+iy-1)*(n1*n2)+(i2+ix)*n1+i1+it]+d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it])))/lambda-rn*d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it];
				    }
				    else {
					aa[i] = (lambda2*aa[i]+lambda1*st[i2*na+i]+lambda3*sy[i1*n2*na+i2*na+i])/lambda-rn*d[(i3+iy)*(n1*n2)+(i2+ix)*n1+i1+it];				    
				    }
				    i++;
				}
			    }
			}
		    }
		}
		for (i=0; i < na; i++) {
		    st[i2*na+i]=aa[i];
		}
		for (i=0; i < na; i++) {
		    sy[i1*n2*na+i2*na+i]=aa[i];
		}
	    }
	}
    }
    
    sf_floatwrite(d,n123,out);
    sf_warning(".");
    exit(0);  
}

