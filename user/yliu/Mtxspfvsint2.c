/* Interpolation using t-x streaming prediction filter with varying smoothness. */
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
    int i1, i2, it, ix, n1, n2, n12, dim, na, i, nst, seed;
    int a[SF_MAX_DIM], n[SF_MAX_DIM];
    int *mask;
    float dd, dea, dn, da, rn, lambda, lambda1, lambda2, epst, epsx, var;
    float *d, *aa, *st;
    
    sf_file in,out,known;
    
    sf_init(argc,argv);
    
    in = sf_input("in");
    out = sf_output("out");
    
    if (!sf_getbool("verb", &verb)) verb = false;
    if (!sf_getbool("smooth", &smooth)) smooth = false;
    
    known = sf_input("known");
    if (SF_INT != sf_gettype(known)) sf_error("Need int type in known");
    
    dim = sf_filedims(in,n);
    if (2 < dim) dim = 2;
    
    if (!sf_getints("a",a,dim)) sf_error("Need a=");
    
    if (dim < 2) sf_error("Need at least two dimension");
    
    n12 = 1;
    na = 1;
    
    for (i=0; i < dim; i++) {
	n12 *= n[i];
	na *= a[i];
    }
    
    n1=n[0];
    n2=n[1];
    nst=na*n2 ;
    
    if (!sf_getfloat("epst",&epst)) epst = 0;
    /* Smoothness in t direction */

    if (!sf_getfloat("epsx",&epsx)) epsx = 0;
    /* Smoothness in x direction */
    
    if (!sf_getfloat("lambda1",&lambda1)) sf_error("Need lambda1=");
    /* Regularization in t direction */
    
    lambda1*=lambda1;
    
    if (!sf_getfloat("lambda2",&lambda2)) sf_error("Need lambda2=");
    /* Regularization in x direction */

    lambda2*=lambda2;
    
    lambda=lambda1+lambda2;
    
    if(verb)
	sf_warning("lambda1=%f, lambda2=%f, lambda=%f", lambda1, lambda2, lambda);
    
    d = sf_floatalloc(n12);
    aa = sf_floatalloc(na);
    st = sf_floatalloc(nst);
    mask = sf_intalloc(n12);
    
    if(verb) sf_warning("Open space.");
    
    sf_intread(mask,n12,known);
    sf_floatread(d,n12,in);
    
    if(verb) sf_warning("Read mask and data.");
    
    if (!sf_getfloat("var",&var)) var=0.0f;
    var = sqrtf(var);
    
    if (!sf_getint("seed",&seed)) seed = time(NULL);
    init_genrand((unsigned long) seed);
    
    for (i=0; i< na; i++) {
	aa[i] = 0.0f;
    }
    for (i=0; i< nst; i++) {
	st[i] = 0.0f;
    }
    if(verb) sf_warning("Initialize filter.");	
    
    for (i1=0; i1 < n1; i1++) {
	for (i2=0; i2 < n2; i2++) {
	    dd = 0.0f;
	    dea = 0.0f;
	    da = 0.0f;
	    i=0;
	    for (ix=-(a[1]-1)/2; ix < (a[1]+1)/2; ix++) {
		for (it=-(a[0]-1)/2; it < (a[0]+1)/2; it++) {
		    if(ix!=0) {
			if(i2+ix-1<0 || i1+it-1<0 || i1+it>n1 || i2+ix>n2) {
			    i++;
			}
			else {
			    dd += d[(i2+ix)*n1+i1+it]*
				d[(i2+ix)*n1+i1+it];
			    da += d[(i2+ix)*n1+i1+it]*
				(lambda2*aa[i]+lambda1*st[i2*na+i])/lambda;
			    if(smooth) {
				dea +=d[(i2+ix)*n1+i1+it]*(lambda2*aa[i]*(1+epsx*(d[(i2+ix-1)*n1+i1+it]-d[(i2+ix)*n1+i1+it]))+lambda1*st[i2*na+i]*(1+epst*(d[(i2+ix)*n1+i1+it-1]-d[(i2+ix)*n1+i1+it])))/lambda;
			    }
			    else {
				dea += d[(i2+ix)*n1+i1+it]*
				    (lambda2*aa[i]+lambda1*st[i2*na+i])/lambda;
			    }
			    i++;
			}
		    }
		}
	    }
	    if(mask[i2*n1+i1]) {
		dn = d[i2*n1+i1];
		rn = (-dn + dea) / (lambda + dd);
	    }
	    else {
		rn = var * sf_randn_one_bm() / lambda;
		dn = rn*(lambda+dd)+da;
		d[i2*n1+i1] = dn;
	    }
	    
	    i=0;
	    for (ix=-(a[1]-1)/2; ix < (a[1]+1)/2; ix++) {
		for (it=-(a[0]-1)/2; it < (a[0]+1)/2; it++) {
		    if(ix!=0) {
			if(i2+ix-1<0 || i1+it-1<0 || i1+it>n1 || i2+ix>n2) {
			    i++;
			}
			else {
			    if(smooth) {
				aa[i] = (lambda2*aa[i]*(1+epsx*(d[(i2+ix-1)*n1+i1+it]-d[(i2+ix)*n1+i1+it]))+lambda1*st[i2*na+i]*(1+epst*(d[(i2+ix)*n1+i1+it-1]-d[(i2+ix)*n1+i1+it])))/lambda-rn*d[(i2+ix)*n1+i1+it];
			    }			
			    else {
				aa[i] = (lambda2*aa[i]+lambda1*st[i2*na+i])/
				    lambda-rn*d[(i2+ix)*n1+i1+it]; 
			    }
			    i++;
			}
		    }
		}
	    }
	    for (i=0; i < na; i++) {
		st[i2*na+i]=aa[i];
	    }
	}
    }
    
    sf_floatwrite(d,n12,out);
    sf_warning(".");
    exit(0);  
}

