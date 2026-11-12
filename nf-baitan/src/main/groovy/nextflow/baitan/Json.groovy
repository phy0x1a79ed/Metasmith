package nextflow.baitan

import groovy.json.JsonSlurper
import groovy.transform.CompileStatic

/**
 * Compact JSON in the exact byte form of serde_json's `to_vec`: no whitespace, map keys in
 * iteration order, non-ASCII left as UTF-8, control characters escaped as serde_json does.
 * Identity hashes depend on these bytes, so do not swap in another encoder.
 */
@CompileStatic
class Json {

    static String encode(Object value) {
        def sb = new StringBuilder()
        write(sb, value)
        return sb.toString()
    }

    static Object parse(String text) {
        return new JsonSlurper().parseText(text)
    }

    private static void write(StringBuilder sb, Object v) {
        if( v == null )
            sb.append('null')
        else if( v instanceof CharSequence )
            string(sb, v.toString())
        else if( v instanceof Boolean || v instanceof Integer || v instanceof Long )
            sb.append(v.toString())
        else if( v instanceof Double || v instanceof BigDecimal ) {
            if( v instanceof Double && !Double.isFinite(((Double) v).doubleValue()) )
                throw new IllegalArgumentException("Cannot encode ${v}")
            sb.append(v.toString())
        }
        else if( v instanceof Map ) {
            sb.append('{')
            boolean first = true
            for( Map.Entry e : ((Map) v).entrySet() ) {
                if( !first ) sb.append(',')
                first = false
                string(sb, e.key.toString())
                sb.append(':')
                write(sb, e.value)
            }
            sb.append('}')
        }
        else if( v instanceof Iterable ) {
            sb.append('[')
            boolean first = true
            for( Object x : (Iterable) v ) {
                if( !first ) sb.append(',')
                first = false
                write(sb, x)
            }
            sb.append(']')
        }
        else
            throw new IllegalArgumentException("Cannot encode ${v.getClass().name}")
    }

    private static void string(StringBuilder sb, String s) {
        sb.append('"')
        for( int i = 0; i < s.length(); i++ ) {
            char c = s.charAt(i)
            switch( c ) {
                case '"': sb.append('\\"'); break
                case '\\': sb.append('\\\\'); break
                case '\n': sb.append('\\n'); break
                case '\r': sb.append('\\r'); break
                case '\t': sb.append('\\t'); break
                case '\b': sb.append('\\b'); break
                case '\f': sb.append('\\f'); break
                default:
                    if( c < 0x20 ) sb.append(String.format('\\u%04x', (int) c))
                    else sb.append(c)
            }
        }
        sb.append('"')
    }
}
