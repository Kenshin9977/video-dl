#!/bin/bash

intel_apus="^Intel (Celeron G1101|Pentium G69..|Core i3-5.0|Core i5-6.0|Core i5-655K|Core i5-661|Celeron U3...|Pentium U5...|Core i3-3.0UM|Core i5-5.0UM|Core i7-6.0UE|Core i7-6.0UM|Core i7-620LE|Core i7-6.0LM|Celeron P4...|Pentium P6...|Core i3-330E|Core i3-3.0M|Core i5-4.0M|Core i5-520E|Core i5-5.0M|Core i7-610E|Core i7-6.0M|Celeron B7.0|Celeron 8.7|Celeron B8..|Pentium B9.0|Pentium 9.7|Celeron G4.0|Celeron G5.0|Celeron G530T|Pentium G6..|Pentium G6.0T|Pentium G8.0|Core i3-2102|Core i3-21.0|Core i3-21.0T|Core i5-2..0|Core i5-2.00S|Core i5-2..0T|Core i7-2600|Core i7-2600S|Xeon E3-1260L|Core i3-23.0E|Core i3-23..M|Core i5-251.E|Core i5-2...M|Core i7-2...QM|Core i7-271.QE|Core i7-29.0XM|Core i3-21.5|Core i5-2405S|Core i5-2500K|Core i7-2.00K|Xeon E3-12.5|Atom Z3735D|Atom Z3735E|Atom Z3735F|Atom Z3735G|Atom Z3736F|Atom Z3736G|Atom Z3680|Atom Z3740|Atom Z3770|Atom Z3680D|Atom Z3740D|Atom Z3770D|Atom Z3745|Atom Z3775|Atom Z3795|Atom Z3745D|Atom Z3775D|Atom Z3785|Celeron N2805|Celeron N2807|Celeron N2830|Pentium N3510|Celeron N2806|Celeron N2810|Celeron N2815|Celeron N2820|Celeron N2910|Celeron N2808|Celeron N2840|Celeron N2920|Celeron N2930|Celeron N2940|Pentium N3520|Pentium N3530|Pentium N3540|Atom E3815|Atom E3825|Atom E3826|Atom E3827|Atom E3845|Celeron J1750|Celeron J1800|Celeron J1850|Celeron J1900|Pentium J2850|Pentium J2900|Pentium A1020|Celeron 16.0|Celeron 1610T|Pentium 2..0|Pentium G2..0T|Celeron 10.0M|Celeron 10.7U|Pentium 2117U|Pentium 20.0M|Xeon E3-1265LV2|Core i3-32.0|Core i3-32.0T|Core i5-3..0|Core i5-3..0S|Core i5-3..0T|Core i3-3225|Core i3-3245|Core i5-3475S|Core i5-3570K|Core i7-3770|Core i7-3770.|Core i3-3110M|Core i3-3120M|Core i5-3210M|Core i3-3120ME|Core i3-3217U|Core i5-3317U|Core i3-3217UE|Core i3-3229Y|Core i5-3339Y|Core i5-3439Y|Core i5-33.0M|Core i5-3337U|Core i5-3427U|Core i5-3610ME|Core i7-3520M|Core i7-3..7U|Core i7-3...QM|Core i7-3920XM|Xeon E3-12.5V2|Pentium G3...|Pentium G3...T|Celeron G18..|Celeron G18..T|Celeron 2950M|Pentium 3550M|Celeron 29..U|Pentium 35..U|Celeron 29..Y|Pentium 35..Y|Core i3-40..Y|Core i5-4...Y|Core i7-4610Y|Core i3-4130|Core i3-4150|Core i3-4160|Core i3-4170|Core i3-4130T|Core i3-4150T|Core i3-4160T|Core i3-4170T|Core i3-4005U|Core i3-4025U|Core i3-4010U|Core i3-4100U|Core i5-4200U|Core i3-4030U|Core i3-4120U|Core i5-4300U|Core i7-4500U|Core i7-4600U|Core i3-4330|Core i3-4340|Core i5-4570|Core i5-4570S|Core i3-4330T|Core i5-4570T|Core i5-4430|Core i5-4430S|Core i5-4440|Core i5-4440S|Core i5-4670|Core i5-4670K|Core i5-4670S|Core i5-4670T|Core i7-4765T|Core i7-4770|Core i7-4770S|Core i7-4770T|Core i7-4771|Core i7-4770K|Core i3-4...E|Core i5-4402E|Core i3-4...M|Core i5-4200M|Core i5-4200H|Core i7-47..MQ|Core i7-4702HQ|Core i5-43..M|Core i5-4400E|Core i7-4700EQ|Core i7-4700HQ|Core i7-4...M|Core i7-4800MQ|Core i7-4900MQ|Core i7-4930MX|Xeon E3-1225 v3|Xeon E3-1226 v3|Xeon E3-1245 v3|Xeon E3-1246 v3|Xeon E3-1275 v3|Xeon E3-1276 v3|Xeon E3-1285L v3|Xeon E3-1286L v3|Xeon E3-1285 v3|Xeon E3-1286 v3|Core i5-4250U|Core i5-4350U|Core i7-4550U|Core i7-4650U|Core i3-4158U|Core i5-4258U|Core i5-4288U|Core i7-4558U|Core i5-4570R|Core i5-4670R|Core i7-4770R|Core i7-4750HQ|Core i7-4850HQ|Core i7-49..HQ|Atom .5-Z8300|Atom .5-Z8500|Celeron N3000|Celeron N3050|Celeron N3150|Atom .7-Z8700|Pentium N3700|Atom .5-Z8350|Celeron N3010|Celeron N3060|Celeron N3160|Celeron J3060|Celeron J3160|Pentium N3710|Pentium J3710|Celeron 3205U|Celeron 3755U|Pentium 3805U|Celeron 3215U|Celeron 3765U|Pentium 3825U|Core M-5Y10|Core M-5Y10a|Core M-5Y10c|Core M-5Y70|Core M-5Y31|Core M-5Y51|Core M-5Y71|Core i3-5005U|Core i3-5015U|Core i3-5010U|Core i3-5020U|Core i5-5200U|Core i5-5300U|Core i7-5500U|Core i7-5600U|Core i7-5700EQ|Core i7-5700HQ|Xeon E3-1258L v4|Core i5-5250U|Core i5-5350U|Core i7-5550U|Core i7-5650U|Core i3-5157U|Core i5-5257U|Core i5-5287U|Core i7-5557U|Core i5-5575R|Core i5-5675C|Core i5-5675R|Core i7-5775C|Core i7-5775R|Core i7-5850EQ|Core i5-5350H|Core i7-5750HQ|Core i7-5850HQ|Core i7-5950HQ|Xeon E3-1278L v4|Xeon E3-1265L v4|Xeon E3-1285 v4|Xeon E3-1285L v4|Atom .5-E3930|Atom .5-E3940|Celeron N3350|Celeron N3450|Celeron J3355|Celeron J3455|Atom .7-E3950|Pentium N4200|Pentium J4205|Celeron 3855U|Celeron 3955U|Pentium 4405U|Celeron G3900TE|Celeron G3900E|Celeron G3900T|Celeron G3900|Celeron G3902E|Celeron G3920|Pentium G4400TE|Pentium G4400T|Core i5-6402P|Pentium G4400|Core i3-6098P|Pentium 4405Y|Core m3-6Y30|Core m5-6Y54|Core m5-6Y57|Core m7-6Y75|Core i3-6006U|Core i3-6100U|Core i5-6200U|Core i5-6300U|Core i7-6500U|Core i7-6600U|Core i3-6100H|Core i3-6100E|Core i3-6102E|Core i5-6300HQ|Core i5-6440HQ|Core i5-6440EQ|Core i5-6442EQ|Core i7-6820EQ|Core i7-6822EQ|Core i7-6700HQ|Core i7-6820HK|Core i7-6820HQ|Core i7-6920HQ|Pentium G4500T|Core i3-6100T|Core i3-6300T|Core i5-6400T|Core i5-6400|Core i3-6100TE|Core i5-6500TE|Core i7-6700TE|Core i7-6700T|Pentium G4500|Pentium G4520|Core i3-6100|Core i5-6500|Core i5-6500T|Core i5-6600T|Core i7-6700|Core i3-6300|Core i3-6320|Core i5-6600|Core i5-6600K|Core i7-6700K|Xeon E3-1268L v5|Xeon E3-1505L v5|Xeon E3-1505M v5|Xeon E3-1535M v5|Xeon E3-1225 v5|Xeon E3-1235L v5|Xeon E3-1245 v5|Xeon E3-1275 v5|Core i5-6260U|Core i5-6360U|Core i7-6560U|Core i7-6650U|Core i7-6660U|Core i3-6157U|Core i3-6167U|Core i5-6267U|Core i5-6287U|Core i7-6567U|Xeon E3-1558L v5|Core i5-6350HQ|Core i7-6770HQ|Core i7-6870HQ|Core i7-6970HQ|Core i5-6585R|Core i5-6685R|Core i7-6785R|Xeon E3-1578L v5|Xeon E3-1515M v5|Xeon E3-1545M v5|Xeon E3-1575M v5|Xeon E3-1565L v5|Xeon E3-1585L v5|Xeon E3-1585 v5|Celeron N4000|Celeron N4100|Celeron J4005|Celeron J4105|Pentium Silver N5000|Pentium Silver J5005|Celeron 3865U|Celeron 3965U|Pentium 4415U|Celeron G3930TE|Celeron G3930E|Celeron G3930T|Celeron G3930|Celeron G3950|Pentium G4560T|Pentium G4560|Core i3-7101TE|Core i3-7101E|Celeron 3965Y|Pentium 4410Y|Pentium 4415Y|Celeron G4950|Celeron G4...|Pentium Gold G5620|Pentium Gold G5420|Core m3-7Y30|Core m3-7Y32|Core i5-7Y54|Core i5-7Y57|Core i7-7Y75|Core i3-7100U|Core i3-7130U|Core i5-7200U|Core i7-7500U|Core i5-7300U|Core i7-7600U|Core i5-8250U|Core i5-8350U|Core i7-8550U|Core i7-8650U|Core i5-7400T|Core i5-7400|Pentium G4600T|Pentium G4600|Pentium G4620|Pentium Gold G4...|Pentium Gold G5...|Core i3-7100T|Core i3-7100|Core i3-7300T|Core i5-7500T|Core i5-7500|Core i5-7600T|Core i3-7300|Core i3-7320|Core i3-7350K|Core i5-7600|Core i5-7600K|Core i7-7700T|Core i7-7700|Core i7-7700K|Core i3-7100E|Core i3-7100H|Core i3-7102E|Core i5-7300HQ|Core i5-7440EQ|Core i5-7440HQ|Core i5-7442EQ|Core i7-7820EQ|Core i7-7700HQ|Core i7-7820HK|Core i7-7820HQ|Core i7-7920HQ|Xeon E3-1501L v6|Xeon E3-1501M v6|Xeon E3-1505L v6|Xeon E3-1505M v6|Xeon E3-1535M v6|Xeon E3-1225 v6|Xeon E3-1245 v6|Xeon E3-1275 v6|Core i5-7260U|Core i5-7360U|Core i7-7560U|Core i7-7660U|Core i3-7167U|Core i5-7267U|Core i5-7287U|Core i7-7567U|Core i3-8100|Core i3-8350K|Core i3-9320|Core i3-9300|Core i3-9100|Core i5-8400|Core i5-8600K|Core i5-9400|Core i5-9500|Core i5-9600|Core i5-9600K|Core i7-8700|Core i7-8700K|Core i7-9700|Core i7-9700K|Core i9-9900|Core i9-9900K|Core i3-10\d\dG(1|4)|i5-10\d\dG(1|4|7)|i7-10\d\dG7)$"
amd_apus="^AMD (A4 (Micro-6400T|Pro-3340B|Pro-3350B|PRO-7300B|PRO-7350B=)|A4-(1200|1250|1350|4000|4020|4300M|4355M|5000|5100|5145M|5150M|5300|5300B|6210|6250J|6300|6300B|6320|6320B|7210|7300|9120)|A6 (Pro-7050B|PRO-7400B)|A6-(1450|4400M|4455M|5200|5345M|5350M|5357M|5400B|5400K|6310|6400B|6400K|6420B|6420K|7000|7310|7400K|7470K|8500P|9200|9200e|9210|9220|9500|9500E|9550)|A8 (Pro-7150B|PRO-7600B)|A8-(4500M|4555M|5500|5500B|5545M|5550M|5557M|5600K|6410|6500|6500B|6500T|6600K|7100|7200P|7410|7600|7650K|7670K|8600P|9600)|A9-(9400|9410|9420|9430)|A10 (Micro-6700T|Pro-7350B|PRO-7800B|PRO-7850B)|A10-(4600M|4655M|5700|5745M|5750M|5757M|5800B|5800K|6700|6700T|6790B|6790K|6800B|6800K|7300|7400P|7700K|7800|7850K|7860K|7870K|7890K|8700P|8780P|9600P|9620P|9630P|9700|9700E)|A12-(9700P|9720P|9730P|9800|9800E)|Athlon (5150|5350|5370)|E1 Micro-6200T|E1-(2100|2200|2500|6010|6015|7010)|E2-(3000|3800|6110|7110|9000|9000e|9010)|FirePro (A300|A320)|FX-(7500|7600P|8800P|9800P|9830P)|GX-(210HA|210JA|217GA|415GA|420CA)|Pro A4-4350B|Pro A6-(7350B|8500B|8530B|8570|8570E|9500|9500B|9500E)|Pro A8-(8600B|9600|9600B|9630B)|Pro A10-(8700B|8730B|8770|8770E|9700|9700B|9700E|9730B)|Pro A12-(8800B|8830B|8870|8870E|9800|9800B|9800E|9830B)|Ryzen 3 ((Pro )?(2|3|4|5)(2|3|4)(0|5)0(GE?|U)|(Pro )?(3|4)(2|4)(0|5)0(GE?|U))|Ryzen 5 ((Pro )?(2|3|4|5)(4|5|6)(0|5|8)0(GE?|U|(HS?)|C))|Ryzen 7 ((Pro )?(2|3|4|5)(7|8)(0|5|8)0(GE?|U|HS?|C))|Ryzen 9 ((4|5)9(0|8)0H(S|X)?)|Sempron (2650|3850)).*"

nvenc_capable="false"
qsv_capable="false"
vce_capable="false"

get_cpu_encoder() {

    # There might be a more efficient way of getting the name of the CPU, but this works for non-BSD Unix systems
    cpu=$(cat /proc/cpuinfo | grep 'model name' | uniq | cut -f2 -d":" | xargs | sed -E 's/^|\(R\)|\(TM\)|CPU |^W\s+ |\w+-Core|Processor|\@.*//g' | xargs)

    if [[ $cpu =~ $amd_apus ]]; then
        vce_capable="true"
    fi

    if [[ $cpu =~ $intel_apus ]]; then
        qsv_capable="true"
    fi

    return
}


get_gpu_encoder() {
    
    gpu_names=($(lspci -mm | grep -i 'VGA\|3D\|2D' | tr -s ' ' '_'))
    for gpu in "${gpu_names[@]}"; do
        name=$(echo $gpu | tr -s '_' ' ')

        if [[ $name =~ "NVIDIA" ]]; then
            nvenc_capable="true"
        fi

        if [[ $name =~ "AMD" ]]; then
            vce_capable="true"
        fi

        if [[ $name =~ "Intel" ]]; then
            qsv_capable="true"
        fi
    done
    
    return
}

choose_encoder() {

    if [ $nvenc_capable = "true" ]; then
        encoder="NVENC"
    elif [ $qsv_capable = "true" ]; then
        encoder="QSV"
    elif [ $vce_capable = "true" ]; then
        encoder="VCE"
    else
        encoder="x264"
    fi

    return
}

get_cpu_encoder

if type lspci > /dev/null; then
    get_gpu_encoder
fi

choose_encoder

echo $encoder
