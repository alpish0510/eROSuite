#!/bin/tcsh 

if ($#argv < 3) then 
    echo   "Usage: cmp_FWCratio.csh Emin Emax TM [proc=...]"
    exit
endif


set Emin=( $1 ) 
set Emax=( $2 )
if ($3 == 0) then
	@ TMmin=0
	@ TMmax=7
else
	@ TMmin=$3
	@ TMmin--
	@ TMmax=$3
endif
@ Nargs=3

set proc=c946
set refEmin=( 6.0 )
set refEmax=( 9.0 )
if ($#argv > $Nargs) then
  while ($Nargs < $#argv) 
      @ Nargs++
      set optstr=( ${argv[$Nargs]} )
      # Check option format
      set check=`echo $optstr | grep =`
      set opttype=`echo $optstr | cut -d= -f1`
      set optval=`echo $optstr | cut -d= -f2`
      if ( ("$check" != "$optstr") || \
           ("a${opttype}a" == 'aa') || ("a${optval}a" == 'aa') ) then
     	  	echo "Invalid format for pipeline option: '$optstr'"
		exit
      endif  
      # Set option
      set check=0
      set opttype=`echo $optstr | cut -d= -f1 | tr '[A-Z]' '[a-z]'`
      if ($opttype == 'proc') then
                if (($optval != 'c946') && ($optval != 'c946Full') && ($optval != 'c946Match020') && ($optval != 'c946Match010') && ($optval != 'c020') && ($optval != 'c020EDR') && ($optval != 'c020Match') && ($optval != 'c010') && ($optval != 'c010EDR') && ($optval != 'c010Match')) then
			echo "Invalid keyword value: processing can only be c946, c010 or c020"
			exit
		endif
		set proc=$optval
		set check=1
      endif
      if ($opttype == 'refemin') then
		set refEmin=( $optval )
		set check=1
      endif
      if ($opttype == 'refemax') then
		set refEmax=( $optval )
		set check=1
      endif
     # Final check
      if ($check == 0) then
      	echo "Unknown optional argument: '$opttype'"
        exit
      endif
  end
endif
endif

# select data processing
set BgdDir=/home/asrivast/eRASS1/Background
switch ($proc)
   case c946:
	set dataDir=${BgdDir}/c946/Spectra/PMENV2/All
        breaksw
   case c946Full:
	set dataDir=${BgdDir}/c946/Spectra/PMENV2/Full
        breaksw
   case c946Match020:
	set dataDir=${BgdDir}/c946/Spectra/PMENV2/AllMatch020
        breaksw
   case c946Match010:
	set dataDir=${BgdDir}/c946/Spectra/PMENV2/AllMatch010
        breaksw
   case c020:
	set dataDir=${BgdDir}/c020/Spectra/PMENV2/All
        breaksw
   case c020EDR:
	set dataDir=${BgdDir}/c020/Spectra/PMENV2/AllEDR
        breaksw
   case c020Match:
	set dataDir=${BgdDir}/c020/Spectra/PMENV2/AllMatch
        breaksw
   case c010:
	set dataDir=${BgdDir}/FWC_c010
        breaksw
   case c010EDR:
	set dataDir=${BgdDir}/c010/Spectra/PMENV2/AllEDR
        breaksw
   case c010Match:
	set dataDir=${BgdDir}/c010/Spectra/PMENV2/AllMatch
        breaksw
endsw
if !(-d ${dataDir}) then
     echo "Could not find spectra for processing ${proc}"
     exit
endif

# Check spectra
@ i=$TMmin
while ($i < $TMmax)
   @ i++
   if !(-f ${dataDir}/TM${i}_FWC_AllPat_spectra.fits) then
       echo "Could not find TM${i} spectrum for processing ${proc}"
       exit  
   endif
end

# Checking soft band inputs
@ Nenergy=$#Emin
if ( $#Emax != $Nenergy ) then
   echo "Number of input energies do not match (#Emin != #Emax)"
   exit
endif 
if ($Nenergy > 0) then
   @ i=1
   while ( $i < $Nenergy )
      set OldEmin=$Emin[$i]
      set OldEmax=$Emax[$i]
      @ i++
      if ( `echo $OldEmin $Emin[$i] | awk '{if($1 > $2){print 1}else{print 0}}'` ) then
         echo "Values of Emin must be in increasing order"
         exit
      endif
      if ( `echo $OldEmax $Emax[$i] | awk '{if($1 > $2){print 1}else{print 0}}'` ) then
         echo "Values of Emax must be in increasing order"
         exit
      endif
      if ( `echo $OldEmax $Emin[$i] | awk '{if($1 > $2){print 1}else{print 0}}'` ) then 
         @ j=$i
         @ j--
         echo 'Input energy interval must be disjoint ( Emax['$j']='$OldEmax' > Emin['$i']='$Emin[$i]')'
         exit
      endif
      
   end
   @ i=0
   while ( $i < $Nenergy )
      @ i++
      if ( `echo $Emin[$i] $Emax[$i] | awk '{if($1 > $2){print 1}else{print 0}}'` ) then
         echo 'Values of Emax should be larger than those of Emin ( Emin['$i']='$Emin[$i]' > Emax['$i']='$Emax[$i]')'
         exit
      endif      
   end
endif

# Checking hard band inputs
@ NrefEn=$#refEmin
if ( $#refEmax != $NrefEn ) then
   echo "Number of input energies for the reference band do not match (#refEmin != #refEmax)"
   exit
endif 
if ($NrefEn > 0) then
   @ i=1
   while ( $i < $NrefEn )
      set OldRefEmin=$refEmin[$i]
      set OldRefEmax=$refEmax[$i]
      @ i++
      if ( `echo $OldRefEmin $refEmin[$i] | awk '{if($1 > $2){print 1}else{print 0}}'` ) then
         echo "Values of refEmin must be in increasing order"
         exit
      endif
      if ( `echo $OldRefEmax $refEmax[$i] | awk '{if($1 > $2){print 1}else{print 0}}'` ) then
         echo "Values of refEmax must be in increasing order"
         exit
      endif
      if ( `echo $OldRefEmax $refEmin[$i] | awk '{if($1 > $2){print 1}else{print 0}}'` ) then 
         @ j=$i
         @ j--
         echo 'Input energy interval must be disjoint ( refEmax['$j']='$OldRefEmax' > refEmin['$i']='$refEmin[$i]')'
         exit
      endif
      
   end
   @ i=0
   while ( $i < $NrefEn )
      @ i++
      if ( `echo $refEmin[$i] $refEmax[$i] | awk '{if($1 > $2){print 1}else{print 0}}'` ) then
         echo 'Values of Emax should be larger than those of Emin ( refEmin['$i']='$refEmin[$i]' > refEmax['$i']='$refEmax[$i]')'
         exit
      endif      
   end
endif

set dateStamp=`date +%s%N`
@ i=0
while (-d /tmp/ero_FWCratio_${dateStamp}_${i})
   @ i++
end
set tmpDir="/tmp/ero_FWCratio_${dateStamp}_${i}"
mkdir ${tmpDir}

xspec <<STOP_XSPEC >> ${tmpDir}/log
   cd ${tmpDir}
   set fileid [ open TMratios.dat w ]
   set TM ${TMmin}
   set refEmin "$refEmin"
   set refEmax "$refEmax"
   set Emin "$Emin"
   set Emax "$Emax"
   while { \$TM < ${TMmax}} {
      set TM [ expr \$TM + 1] 
      puts \$TM
      # Load data
      cd ${dataDir}
      data TM\${TM}_FWC_AllPat_spectra.fits
      cd ${tmpDir}
      # Estimate reference band rate
      set HardRate 0.0
      for {set i 0} {\$i < $NrefEn} {incr i} {
      	notice **
      	ignore bad
      	ignore *:**-[lindex \$refEmin \$i] 
      	ignore *:[lindex \$refEmax \$i]-** 
      	tclout rate 1
      	set HardRate [expr \$HardRate + [ lindex \$xspec_tclout 0 ] ]
      } 
      # Estimate band rate
      set BandRate 0.0
      for {set i 0} {\$i < $Nenergy} {incr i} {
      	notice **
      	ignore bad
      	ignore *:**-[lindex \$Emin \$i]
      	ignore *:[lindex \$Emax \$i]-** 
      	tclout rate 1
      	set BandRate [expr \$BandRate + [ lindex \$xspec_tclout 0 ] ]
      }
      puts \$fileid [ expr \$BandRate  / \$HardRate ]
   }
   close \$fileid  
   exit
STOP_XSPEC

cat ${tmpDir}/TMratios.dat

/bin/rm -rf ${tmpDir}