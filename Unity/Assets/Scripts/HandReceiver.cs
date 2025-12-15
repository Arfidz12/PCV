using UnityEngine;
using extOSC;

public class HandReceiver : MonoBehaviour
{
    public string oscAddress = "/hand/0/8"; // contoh: telunjuk kiri
    public Transform fingerBone; // drag bone dari avatar di inspector

    private OSCReceiver receiver;

    void Start()
    {
        receiver = gameObject.AddComponent<OSCReceiver>();
        receiver.LocalPort = 5065; // harus sama dengan Python
        receiver.Bind(oscAddress, OnReceiveFinger);
    }

    void OnReceiveFinger(OSCMessage message)
    {
        var x = message.Values[0].FloatValue;
        var y = message.Values[1].FloatValue;
        var z = message.Values[2].FloatValue;

        // Mapping ke Unity world (butuh scaling/offset sesuai avatar)
        fingerBone.localPosition = new Vector3(x, y, z);
    }
}
