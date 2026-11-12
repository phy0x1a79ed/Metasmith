package nextflow.baitan

import java.security.MessageDigest

import groovy.transform.CompileStatic

/**
 * Port of baitan-proto's identity hashing: `instance_id`, `offer_key` and `slot_id`.
 * Each is the first 16 bytes of the SHA-256 of a compact JSON encoding, hex-encoded.
 * A prop map is sorted by key (Rust `BTreeMap`); `spec` keeps the order it is given
 * (serde_json `preserve_order`), so callers must build it in one fixed order.
 */
@CompileStatic
class Ids {

    static String instanceId(Map<String,String> props) {
        return h(Json.encode(new TreeMap<String,String>(props)))
    }

    static String offerKey(String op, Map<String,String> props, List<String> inputs, Object spec, String to) {
        return h(Json.encode([op, new TreeMap<String,String>(props), inputs, spec, to]))
    }

    static String slotId(String offerKey, String slot) {
        return h(Json.encode([offerKey, slot]))
    }

    private static String h(String json) {
        final digest = MessageDigest.getInstance('SHA-256').digest(json.getBytes('UTF-8'))
        final sb = new StringBuilder(32)
        for( int i = 0; i < 16; i++ )
            sb.append(String.format('%02x', digest[i] & 0xff))
        return sb.toString()
    }
}
