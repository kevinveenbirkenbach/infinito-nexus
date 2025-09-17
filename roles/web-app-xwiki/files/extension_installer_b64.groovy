// Reads Base64 JSON from placeholder and avoids any quoting issues.
import groovy.json.JsonSlurper
import java.util.Base64

def ext = services.extension
def ns  = "wiki:xwiki"

def b64 = '__WANTED_B64__'
def json = new String(Base64.decoder.decode(b64), 'UTF-8')
def wanted = new JsonSlurper().parseText(json) as List<Map>

if (!wanted || wanted.isEmpty()) {
  println "SKIP: no extensions requested"
  return
}

wanted.each { e ->
  def id  = (e.id ?: "").toString()
  def ver = (e.version ?: "").toString().trim()
  if (!id) { println "ERROR::<missing-id>::Empty extension id in wanted list"; return }

  def already = ext.getInstalledExtension(id, ns)
  if (already) { println "ALREADY_INSTALLED::${id}::${already.id?.version}"; return }

  println "INSTALL_START::${id}::${ver ? ver : 'latest'}"
  def job
  try {
    job = ver ? ext.install(id, ver, ns) : ext.install(id, null, ns)
    job?.join()
  } catch (Throwable t) {
    println "ERROR::${id}::${(t?.message ?: t?.toString())}"
  }

  def st = job?.status?.state?.name()
  if (st) println "STATE=${st}::${id}"

  def err = job?.status?.error  // singular!
  if (err) println "ERROR::${id}::${(err?.message ?: err?.toString())}"

  def now = ext.getInstalledExtension(id, ns)
  if (now) println "INSTALLED_OK::${id}::${now.id?.version}"
  else     println "INSTALLED_MISSING::${id}"
}
