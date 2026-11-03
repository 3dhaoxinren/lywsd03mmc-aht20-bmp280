// From https://pvvx.github.io/ATC_MiThermometer/TelinkMiFlasher.html
var crc32 = (function() {
	let table = new Uint32Array(256);
	for(var i=256; i--;) {
		let tmp = i;
		for(let k=8; k--;) {
			tmp = tmp & 1 ? 0xEDB88320 ^ tmp >>> 1 : tmp >>> 1;
		}
		table[i] = tmp;
	}
	return function( data ) {
		let crc = -1;
		let l = data.length;
		for(let i=0; i<l; i++) {
			crc = crc >>> 8 ^ table[ crc & 255 ^ data[i] ];
		}
		return (crc >>> 0);
	};
})();

function testOTAFirmware(data) {
	let fsize = data.byteLength;
	addClog("File size = 0x"+ fsize.toString(16));
	if (fsize < 1024)
		return "Wrong binary Telink OTA firmware size!";
	let head = new DataView(data, 0, 0x40);
	if(head.getUint32(0, true) == 0x0beef11e) { // Zigbee OTA
		if(head.getUint16(4, true) != 0x100	|| head.getUint16(6, true) != 56)
			return "Unknown Zigbee OTA header!";
		fzigbeeota.size = head.getUint32(0x3A, true);
		if(fzigbeeota.size < 2048 || fzigbeeota.size + 0x3e > fsize)
			return "Wrong binary Zigbee OTA firmware size!";
		fzigbeeota.man_code = head.getUint16(0x0a, true);
		fzigbeeota.image_type = head.getUint16(0x0c, true);
		fzigbeeota.fwversion = head.getUint32(0x0e, true);
		fzigbeeota.ota_version = head.getUint8(0x12);
		fzigbeeota.used = true;
		fsize = fzigbeeota.size;
		addAlog("Zigbee OTA Info: ManCode: "+hex(fzigbeeota.man_code, 4)+ ", ImageType: " + hex(fzigbeeota.image_type,4) + ", FwVer: " + hex(fzigbeeota.fwversion, 8));
		addAlog("APP Release: " + ((fzigbeeota.fwversion >> 28)&0x0f) + "." + ((fzigbeeota.fwversion >> 24)&0x0f)
		+ " Build: " + ((fzigbeeota.fwversion >> 20)&0x0f) + "." + ((fzigbeeota.fwversion >> 16)&0x0f)
		+ ", Stack Version: " + ((fzigbeeota.fwversion >> 12)&0x0f) + "." + ((fzigbeeota.fwversion >> 8)&0x0f)
		+ " Release: " + ((fzigbeeota.fwversion >> 4)&0x0f) + "." + (fzigbeeota.fwversion&0x0f));
		if(!bigOtaEnabled) {
			if(fzigbeeota.image_type >= 0x0203 && fzigbeeota.image_type <= 0x0205)
				return "The current firmware version does not support OTA for image type `"+hex(fzigbeeota.image_type, 4)+"`.";
			if(fsize > fwmaxsize)
				return "The current firmware version does not support EXT OTA. Update the new custom BLE version (4.6 or higher)!";
		} else {
			if(bigOtaEnabled && fsize > MAX_EXT_OTA_SIZE) // 208KB
				return "Size firmware is more 208 kbytes!";
		}
		data = data.slice(0x3e);
	 	head = new DataView(data, 0, 0x20);
	} else {
		fzigbeeota.used = false;
		if(bigOtaEnabled) {
			if (fsize > MAX_EXT_OTA_SIZE) // 208KB
				return "Size firmware is more 208 kbytes!";
		} else if(fsize > fwmaxsize)
			return "Size firmware is more "+fwmaxsize+" bytes!";
	}
	if(head.getUint32(0x08, true) != 0x544c4e4b){
		return "Incorrect head in Telink OTA binary firmware";
	}
	let hsize = head.getUint32(0x18, true);
	addClog("Size in head = 0x" + hsize.toString(16));
	if((hsize > fsize) || ((hsize & 0x0f) != 4)) {
		return "Invalid size pointer in Telink OTA binary firmware!";
	}
	let fcrc = new Uint32Array(2);
	fcrc[0] = crc32(new Uint8Array(data.slice(0, hsize - 4)));
	let x = new DataView(data, hsize - 4, 4);
	fcrc[1] = x.getUint32(0, true);
	addClog("File CRC = 0x" + fcrc[1].toString(16) + ", Check CRC = 0x" + fcrc[0].toString(16));
	if(fcrc[0] != fcrc[1]) {
		return "Incorrect CRC in Telink OTA binary firmware!";
	}
	if((hsize < fsize) && (fsize - hsize  > 1024)) {
	 	if(bytesToHex(data.slice(hsize, hsize + 12)) == "000000004d49ef54464f5441")
			return "sign";
	}
	return "ok";
}

