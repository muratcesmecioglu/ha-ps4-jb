// PSFree & Lapse Helper Subroutines

const off_js_butterfly = 0x8;
const off_js_inline_prop = 0x10;
const off_view_m_vector = 0x10;
const off_view_m_length = 0x18;
const off_view_m_mode = 0x1c;
const off_vector = 0x04; //off_view_m_vector / 4;
const off_vector2 = 0x05; //(off_view_m_vector + 4) / 4;
const off_strimpl_strlen = 4;
const off_strimpl_m_data = 8;
const off_strimpl_inline_str = 0x14;
const off_size_strimpl = 0x18;
const KB = 0x400; //1024;
const MB = 0x100000; //KB * KB;
const page_size = 0x4000; //16 * KB; // page size on ps4
const is_ps4 = 1;

var ssv_len;
var mem;
var text_magic;

function isIntegerFix(x) {
  if (typeof x !== 'number') return 0;
  if (!isFinite(x)) return 0;
  if (Math.floor(x) !== x) return 0;
  return 1;
}

function check_not_in_range(x) {
  if (typeof x !== 'number') return 1;
  if (!isFinite(x)) return 1;
  if (Math.floor(x) !== x) return 1;
  if (x < (-0x80000000)) return 1;
  if (x > 0xffffffff) return 1;
  return 0;
}

// use this if you want to support objects convertible to Int but only need
// their low/high bits. creating a Int is slower compared to just using this
// function
function lohi_from_one(low) {
  if (low instanceof Int) {
    return low._u32.slice();
  }
  if (check_not_in_range(low)) {
    throw TypeError('low not a 32-bit integer');
  }
  return [low >>> 0, low < 0 ? -1 >>> 0 : 0];
}

class DieError extends Error {
  constructor(...args) {
    super(...args);
    this.name = this.constructor.name;
  }
}

function die(msg='') {
  throw new DieError(msg);
}

// immutable 64-bit integer
class Int {
  constructor(low, high) {
    if (high === undefined) {
      this._u32 = new Uint32Array(lohi_from_one(low));
      return;
    }
    if (check_not_in_range(low)) {
      throw TypeError('low not a 32-bit integer');
    }
    if (check_not_in_range(high)) {
      throw TypeError('high not a 32-bit integer');
    }
    this._u32 = new Uint32Array([low, high]);
  }
  get lo() {
    return this._u32[0];
  }
  get hi() {
    return this._u32[1];
  }
  // return low/high as signed integers
  get bot() {
    return this._u32[0] | 0;
  }
  get top() {
    return this._u32[1] | 0;
  }
  neg() {
    const u32 = this._u32;
    const low = (~u32[0] >>> 0) + 1;
    return new this.constructor(
      low >>> 0,
      ((~u32[1] >>> 0) + (low > 0xffffffff)) >>> 0
    );
  }
  eq(b) {
    const values = lohi_from_one(b);
    const u32 = this._u32;
    return (
      u32[0] === values[0]
      && u32[1] === values[1]
    );
  }
  ne(b) {
    return !this.eq(b);
  }
  add(b) {
    const values = lohi_from_one(b);
    const u32 = this._u32;
    const low = u32[0] + values[0];
    return new this.constructor(
        low >>> 0,
        (u32[1] + values[1] + (low > 0xffffffff)) >>> 0
    );
  }
  sub(b) {
    const values = lohi_from_one(b);
    const u32 = this._u32;
    const low = u32[0] + (~values[0] >>> 0) + 1;
    return new this.constructor(
      low >>> 0,
      (u32[1] + (~values[1] >>> 0) + (low > 0xffffffff)) >>> 0
    );
  }
  toString(is_pretty=false) {
    var low, high;
    if (!is_pretty) {
      low = this.lo.toString(16).padStart(8, '0');
      high = this.hi.toString(16).padStart(8, '0');
      return '0x' + high + low;
    }
    high = this.hi.toString(16).padStart(8, '0');
    high = high.substring(0, 4) + '_' + high.substring(4);
    low = this.lo.toString(16).padStart(8, '0');
    low = low.substring(0, 4) + '_' + low.substring(4);
    return '0x' + high + '_' + low;
  }
}

// alignment must be 32 bits and is a power of 2
function align(a, alignment) {
  if (!(a instanceof Int)) {
    a = new Int(a);
  }
  const mask = -alignment & 0xffffffff;
  const type = a.constructor;
  const low = a.lo & mask;
  return new type(low, a.hi);
}

function hex(number) {
  return '0x' + number.toString(16);
}

// no "0x" prefix
function hex_np(number) {
  return number.toString(16);
}

// expects a byte array
// converted to ES5 supported version
function hexdump(view) {
  var len = view.length;
  var num_16 = len & ~15;
  var residue = len - num_16;
  function chr(i) {
    return (0x20 <= i && i <= 0x7e) ? String.fromCharCode(i) : '.';
  }
  function to_hex(view, offset, length) {
    var out = [];
    for (var i = 0; i < length; i++) {
      var v = view[offset + i];
      var h = v.toString(16);
      if (h.length < 2) h = "0" + h;
      out.push(h);
    }
    return out.join(" ");
  }
  var bytes = [];
  // 16-byte blocks
  for (var i = 0; i < num_16; i += 16) {
    var long1 = to_hex(view, i, 8);
    var long2 = to_hex(view, i + 8, 8);
    var print = "";
    for (var j = 0; j < 16; j++) {
      print += chr(view[i + j]);
    }
    bytes.push([long1 + "  " + long2, print]);
  }
  // residual bytes
  if (residue) {
    var small = residue <= 8;
    var long1_len = small ? residue : 8;
    var long1 = to_hex(view, num_16, long1_len);
    if (small) {
      for (var k = residue; k < 8; k++) {
        long1 += " xx";
      }
    }
    var long2;
    if (small) {
      var arr = [];
      for (var k = 0; k < 8; k++) arr.push("xx");
      long2 = arr.join(" ");
    } else {
      long2 = to_hex(view, num_16 + 8, residue - 8);
      for (var k = residue; k < 16; k++) {
        long2 += " xx";
      }
    }
    var printRem = "";
    for (var k = 0; k < residue; k++) {
      printRem += chr(view[num_16 + k]);
    }
    while (printRem.length < 16) printRem += " ";
    bytes.push([long1 + "  " + long2, printRem]);
  }
  // print screen
  for (var pos = 0; pos < bytes.length; pos++) {
    var off = (pos * 16).toString(16);
    while (off.length < 8) off = "0" + off;
    var row = bytes[pos];
    log(off + " | " + row[0] + " |" + row[1] + "|");
  }
}

function gc() {
  new Uint8Array(4 * MB);
}

function add_and_set_addr(mem, offset, base_lo, base_hi) {
  const values = lohi_from_one(offset);
  const main = mem._main;
  const low = base_lo + values[0];
  // no need to use ">>> 0" to convert to unsigned here
  main[off_vector] = low;
  main[off_vector2] = base_hi + values[1] + (low > 0xffffffff);
}

class Addr extends Int {
  read8(offset) {
    const m = mem;
    if (isIntegerFix(offset) && 0 <= offset && offset <= 0xffffffff) {
      m._set_addr_direct(this);
    } else {
      add_and_set_addr(m, offset, this.lo, this.hi);
      offset = 0;
    }
    return m.read8_at(offset);
  }
  read16(offset) {
    const m = mem;
    if (isIntegerFix(offset) && 0 <= offset && offset <= 0xffffffff) {
      m._set_addr_direct(this);
    } else {
      add_and_set_addr(m, offset, this.lo, this.hi);
      offset = 0;
    }
    return m.read16_at(offset);
  }
  read32(offset) {
    const m = mem;
    if (isIntegerFix(offset) && 0 <= offset && offset <= 0xffffffff) {
      m._set_addr_direct(this);
    } else {
      add_and_set_addr(m, offset, this.lo, this.hi);
      offset = 0;
    }
    return m.read32_at(offset);
  }
  read64(offset) {
    const m = mem;
    if (isIntegerFix(offset) && 0 <= offset && offset <= 0xffffffff) {
      m._set_addr_direct(this);
    } else {
      add_and_set_addr(m, offset, this.lo, this.hi);
      offset = 0;
    }
    return m.read64_at(offset);
  }
  readp(offset) {
    const m = mem;
    if (isIntegerFix(offset) && 0 <= offset && offset <= 0xffffffff) {
      m._set_addr_direct(this);
    } else {
      add_and_set_addr(m, offset, this.lo, this.hi);
      offset = 0;
    }
    return m.readp_at(offset);
  }
  write8(offset, value) {
    const m = mem;
    if (isIntegerFix(offset) && 0 <= offset && offset <= 0xffffffff) {
      m._set_addr_direct(this);
    } else {
      add_and_set_addr(m, offset, this.lo, this.hi);
      offset = 0;
    }
    m.write8_at(offset, value);
  }
  write16(offset, value) {
    const m = mem;
    if (isIntegerFix(offset) && 0 <= offset && offset <= 0xffffffff) {
      m._set_addr_direct(this);
    } else {
      add_and_set_addr(m, offset, this.lo, this.hi);
      offset = 0;
    }
    m.write16_at(offset, value);
  }
  write32(offset, value) {
    const m = mem;
    if (isIntegerFix(offset) && 0 <= offset && offset <= 0xffffffff) {
      m._set_addr_direct(this);
    } else {
      add_and_set_addr(m, offset, this.lo, this.hi);
      offset = 0;
    }
    m.write32_at(offset, value);
  }
  write64(offset, value) {
    const m = mem;
    if (isIntegerFix(offset) && 0 <= offset && offset <= 0xffffffff) {
      m._set_addr_direct(this);
    } else {
      add_and_set_addr(m, offset, this.lo, this.hi);
      offset = 0;
    }
    m.write64_at(offset, value);
  }
}

function init_module(memory) {
  mem = memory;
}

// expected:
// * main - Uint32Array whose m_vector points to worker
// * worker - DataView
// addrof()/fakeobj() expectations:
// * obj - has a "addr" property and a 0 index.
// * addr_addr - Int, the address of the slot of obj.addr
// * fake_addr - Int, the address of the slot of obj[0]
// a valid example for "obj" is "{addr: null, 0: 0}". note that this example
// has [0] be 0 so that the butterfly's indexing type is ArrayWithInt32. this
// prevents the garbage collector from incorrectly treating the slot's value as
// a JSObject and then crash
// the relative read/write methods expect the offset to be a unsigned 32-bit
// integer
class Memory {
  constructor(main, worker, obj, addr_addr, fake_addr) {
    this._main = main;
    this._worker = worker;
    this._obj = obj;
    this._addr_low = addr_addr.lo;
    this._addr_high = addr_addr.hi;
    this._fake_low = fake_addr.lo;
    this._fake_high = fake_addr.hi;
    main[off_view_m_length / 4] = 0xffffffff;
    init_module(this);
    if (config_target >= 0x700) {
      const off_mvec = off_view_m_vector;
      // use this to create WastefulTypedArrays to avoid a GC crash
      const buf = new ArrayBuffer(0);
      const src = new Uint8Array(buf);
      const sset = new Uint32Array(buf);
      const sset_p = this.addrof(sset);
      sset_p.write64(off_mvec, this.addrof(src).add(off_mvec));
      sset_p.write32(off_view_m_length, 3);
      this._cpysrc = src;
      this._src_setter = sset;
      const dst = new Uint8Array(buf);
      const dset = new Uint32Array(buf);
      const dset_p = this.addrof(dset);
      dset_p.write64(off_mvec, this.addrof(dst).add(off_mvec));
      dset_p.write32(off_view_m_length, 3);
      dset[2] = 0xffffffff;
      this._cpydst = dst;
      this._dst_setter = dset;
    }
  }
  // dst and src may overlap
  cpy(dst, src, len) {
    if (!(isIntegerFix(len) && 0 <= len && len <= 0xffffffff)) {
      throw TypeError('len not a unsigned 32-bit integer');
    }
    const dvals = lohi_from_one(dst);
    const svals = lohi_from_one(src);
    const dset = this._dst_setter;
    const sset = this._src_setter;
    dset[0] = dvals[0];
    dset[1] = dvals[1];
    sset[0] = svals[0];
    sset[1] = svals[1];
    sset[2] = len;
    this._cpydst.set(this._cpysrc);
  }
  // allocate Garbage Collector managed memory. returns [address_of_memory,
  // backer]. backer is the JSCell that is keeping the returned memory alive,
  // you can drop it once you have another GC object reference the address.
  // the backer is an implementation detail. don't use it to mutate the
  // memory
  gc_alloc(size) {
    if (!isIntegerFix(size)) { throw TypeError('size not a integer'); }
    if (size < 0) { throw RangeError('size is negative'); }
    const fastLimit = 1000;
    size = ((size + 7) & ~7) >> 3;
    if (size > fastLimit) { throw RangeError('size is too large'); }
    const backer = new Float64Array(size);
    return [mem.addrof(backer).readp(off_view_m_vector), backer];
  }
  fakeobj(addr) {
    const values = lohi_from_one(addr);
    const worker = this._worker;
    const main = this._main;
    main[off_vector] = this._fake_low;
    main[off_vector2] = this._fake_high;
    worker.setUint32(0, values[0], true);
    worker.setUint32(4, values[1], true);
    return this._obj[0];
  }
  addrof(object) {
    // typeof considers null as a object. blacklist it as it isn't a
    // JSObject
    if (object === null || (typeof object !== 'object' && typeof object !== 'function')) {
      throw TypeError('argument not a JS object');
    }
    const obj = this._obj;
    const worker = this._worker;
    const main = this._main;
    obj.addr = object;
    main[off_vector] = this._addr_low;
    main[off_vector2] = this._addr_high;
    const res = new Addr(worker.getUint32(0, true), worker.getUint32(4, true));
    obj.addr = null;
    return res;
  }
  // expects addr to be a Int
  _set_addr_direct(addr) {
    const main = this._main;
    main[off_vector] = addr.lo;
    main[off_vector2] = addr.hi;
  }
  set_addr(addr) {
    const values = lohi_from_one(addr);
    const main = this._main;
    main[off_vector] = values[0];
    main[off_vector2] = values[1];
  }
  get_addr() {
    const main = this._main;
    return new Addr(main[off_vector], main[off_vector2]);
  }
  read8(addr) {
    this.set_addr(addr);
    return this._worker.getUint8(0);
  }
  read16(addr) {
    this.set_addr(addr);
    return this._worker.getUint16(0, true);
  }
  read32(addr) {
    this.set_addr(addr);
    return this._worker.getUint32(0, true);
  }
  read64(addr) {
    this.set_addr(addr);
    const worker = this._worker;
    return new Int(worker.getUint32(0, true), worker.getUint32(4, true));
  }
  // returns a pointer instead of an Int
  readp(addr) {
    this.set_addr(addr);
    const worker = this._worker;
    return new Addr(worker.getUint32(0, true), worker.getUint32(4, true));
  }
  read8_at(offset) {
    if (!isIntegerFix(offset)) {
      throw TypeError('offset not a integer');
    }
    return this._worker.getUint8(offset);
  }
  read16_at(offset) {
    if (!isIntegerFix(offset)) {
      throw TypeError('offset not a integer');
    }
    return this._worker.getUint16(offset, true);
  }
  read32_at(offset) {
    if (!isIntegerFix(offset)) {
      throw TypeError('offset not a integer');
    }
    return this._worker.getUint32(offset, true);
  }
  read64_at(offset) {
    if (!isIntegerFix(offset)) {
      throw TypeError('offset not a integer');
    }
    const worker = this._worker;
    return new Int(worker.getUint32(offset, true), worker.getUint32(offset + 4, true));
  }
  readp_at(offset) {
    if (!isIntegerFix(offset)) {
      throw TypeError('offset not a integer');
    }
    const worker = this._worker;
    return new Addr(worker.getUint32(offset, true), worker.getUint32(offset + 4, true));
  }
  write8(addr, value) {
    this.set_addr(addr);
    this._worker.setUint8(0, value);
  }
  write16(addr, value) {
    this.set_addr(addr);
    this._worker.setUint16(0, value, true);
  }
  write32(addr, value) {
    this.set_addr(addr);
    this._worker.setUint32(0, value, true);
  }
  write64(addr, value) {
    const values = lohi_from_one(value);
    this.set_addr(addr);
    const worker = this._worker;
    worker.setUint32(0, values[0], true);
    worker.setUint32(4, values[1], true);
  }
  write8_at(offset, value) {
    if (!isIntegerFix(offset)) {
      throw TypeError('offset not a integer');
    }
    this._worker.setUint8(offset, value);
  }
  write16_at(offset, value) {
    if (!isIntegerFix(offset)) {
      throw TypeError('offset not a integer');
    }
    this._worker.setUint16(offset, value, true);
  }
  write32_at(offset, value) {
    if (!isIntegerFix(offset)) {
      throw TypeError('offset not a integer');
    }
    this._worker.setUint32(offset, value, true);
  }
  write64_at(offset, value) {
    if (!isIntegerFix(offset)) {
      throw TypeError('offset not a integer');
    }
    const values = lohi_from_one(value);
    const worker = this._worker;
    worker.setUint32(offset, values[0], true);
    worker.setUint32(offset + 4, values[1], true);
  }
}

// DataView's accessors are constant time and are faster when doing multi-byte
// accesses but the single-byte accessors are slightly slower compared to just
// indexing the Uint8Array
// to get the best of both worlds, BufferView uses a DataView for multi-byte
// accesses and a Uint8Array for single-byte
// instances of BufferView will their have m_mode set to WastefulTypedArray
// since we use the .buffer getter to create a DataView
class BufferView extends Uint8Array {
  constructor(...args) {
      super(...args);
      this._dview = new DataView(this.buffer, this.byteOffset);
  }
  read8(offset) { return this._dview.getUint8(offset); }
  read16(offset) { return this._dview.getUint16(offset, true); }
  read32(offset) { return this._dview.getUint32(offset, true); }
  read64(offset) {
    return new Int(this._dview.getUint32(offset, true), this._dview.getUint32(offset + 4, true));
  }
  write8(offset, value) { this._dview.setUint8(offset, value); }
  write16(offset, value) { this._dview.setUint16(offset, value, true); }
  write32(offset, value) { this._dview.setUint32(offset, value, true); }
  write64(offset, value) {
    const values = lohi_from_one(value);
    this._dview.setUint32(offset, values[0], true);
    this._dview.setUint32(offset + 4, values[1], true);
  }
}

function sread64(str, offset) {
  const low = str.charCodeAt(offset) | (str.charCodeAt(offset + 1) << 8) | (str.charCodeAt(offset + 2) << 16) | (str.charCodeAt(offset + 3) << 24);
  const high = str.charCodeAt(offset + 4) | (str.charCodeAt(offset + 5) << 8) | (str.charCodeAt(offset + 6) << 16) | (str.charCodeAt(offset + 7) << 24);
  return new Int(low, high);
}

class Reader {
  constructor(rstr, rstr_view) {
    this.rstr = rstr;
    this.rstr_view = rstr_view;
    this.m_data = rstr_view.read64(off_strimpl_m_data);
  }
  read8_at(offset) {
    return this.rstr.charCodeAt(offset);
  }
  read32_at(offset) {
    const str = this.rstr;
    return (str.charCodeAt(offset) | (str.charCodeAt(offset + 1) << 8) | (str.charCodeAt(offset + 2) << 16) | (str.charCodeAt(offset + 3) << 24)) >>> 0;
  }
  read64_at(offset) {
    return sread64(this.rstr, offset);
  }
  read64(addr) {
    this.rstr_view.write64(off_strimpl_m_data, addr);
    return sread64(this.rstr, 0);
  }
  set_addr(addr) {
    this.rstr_view.write64(off_strimpl_m_data, addr);
  }
  // remember to use this to fix up the StringImpl before freeing it
  restore() {
    this.rstr_view.write64(off_strimpl_m_data, this.m_data);
    const original_strlen = ssv_len - off_size_strimpl;
    this.rstr_view.write32(off_strimpl_strlen, original_strlen);
  }
}

function get_view_vector(view) {
  if (!ArrayBuffer.isView(view)) {
    throw TypeError(`object not a JSC::JSArrayBufferView: ${view}`);
  }
  if (mem === null) {
    throw Error('mem is not initialized. make_arw() must be called first to initialize mem.');
  }
  return mem.addrof(view).readp(off_view_m_vector);
}

function rw_write64(u8_view, offset, value) {
  if (!(value instanceof Int)) {
    throw TypeError('write64 value must be an Int');
  }
  const low = value.lo;
  const high = value.hi;
  for (var i = 0; i < 4; i++) {
    u8_view[offset + i] = (low >>> (i * 8)) & 0xff;
  }
  for (var i = 0; i < 4; i++) {
    u8_view[offset + 4 + i] = (high >>> (i * 8)) & 0xff;
  }
}

// these values came from analyzing dumps from CelesteBlue
function check_magic_at(p, is_text) {
  const value = [p.read64(0), p.read64(8)];
  return value[0].eq(text_magic[0]) && value[1].eq(text_magic[1]);
}

function find_base(addr, is_text, is_back) {
  // align to page size
  addr = align(addr, page_size);
  text_magic = [
    new Int(0xe5894855, 0x56415741),
    new Int(0x54415541, 0x8d485053)
  ];
  const offset = (is_back ? -1 : 1) * page_size;
  while (true) {
    if (check_magic_at(addr, is_text)) {
      break;
    }
    addr = addr.add(offset);
  }
  return addr;
}

async function get_patches(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw Error(`Network response was not OK, status: ${response.status}\n` + `failed to fetch: ${url}`);
  }
  return response.arrayBuffer();
}

function Init_Globals() {
  if (config_target < 0x650)
    ssv_len = 0x58;
  else if (config_target < 0x900)
    ssv_len = 0x48;
  else
    ssv_len = 0x50;
}

window.script_loaded = 1;
