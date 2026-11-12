package nextflow.baitan

import groovy.transform.CompileStatic

/**
 * The declared set of a process, from its `ext.baitan`: contract, optional version and source
 * hash, output-affecting params, and the declared property set of each given file it reads.
 */
@CompileStatic
class Declaration {

    final Map<String,String> props
    final Map<String,Map<String,String>> givens

    private Declaration(Map<String,String> props, Map<String,Map<String,String>> givens) {
        this.props = props
        this.givens = givens
    }

    static Declaration of(Object ext) {
        if( !(ext instanceof Map) || !((Map) ext).contract )
            return null
        final m = (Map) ext
        final props = new TreeMap<String,String>()
        props.put('contract', m.contract.toString())
        for( String k : ['version', 'source'] )
            if( m.get(k) ) props.put(k, m.get(k).toString())
        ((m.params ?: [:]) as Map).each { k, v -> props.put("param.${k}".toString(), v.toString()) }
        final givens = new LinkedHashMap<String,Map<String,String>>()
        ((m.givens ?: [:]) as Map).each { k, v -> givens.put(k.toString(), new TreeMap<String,String>((Map<String,String>) v)) }
        return new Declaration(props, givens)
    }

    /** The instance id of a given file, when its property set is declared. */
    String givenId(String path) {
        final p = givens.get(path)
        return p == null ? null : Ids.instanceId(p)
    }
}
