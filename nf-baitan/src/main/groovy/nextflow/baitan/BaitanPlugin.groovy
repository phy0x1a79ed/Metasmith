package nextflow.baitan

import groovy.transform.CompileStatic
import nextflow.plugin.BasePlugin
import org.pf4j.PluginWrapper

/** Entry point of the nf-baitan plugin: registers the `baitan` executor. */
@CompileStatic
class BaitanPlugin extends BasePlugin {

    BaitanPlugin(PluginWrapper wrapper) {
        super(wrapper)
    }
}
