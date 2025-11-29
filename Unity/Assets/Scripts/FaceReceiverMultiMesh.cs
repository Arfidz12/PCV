using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

public class FaceReceiverMultiMesh : MonoBehaviour
{
    public int listenPort = 5065;

    [Header("Mesh Assignments")]
    public SkinnedMeshRenderer mouthMeshRenderer;
    public SkinnedMeshRenderer eyeMeshRenderer;
    public SkinnedMeshRenderer browMeshRenderer;

    [Header("BlendShape Index")]
    public int mouthOpenBlendIndex = 0;
    public int leftEyeBlinkBlendIndex = 0;
    public int rightEyeBlinkBlendIndex = 1;
    public int leftBrowRaiseBlendIndex = 0;
    public int rightBrowRaiseBlendIndex = 1;

    [Header("Blendshape Strength Scaling")]
    public float mouthOpenScale = 100f;
    public float eyeBlinkScale = 100f;
    public float browRaiseScale = 100f;

    volatile float mouthOpen = 0f, leftEyeOpen = 1f, rightEyeOpen = 1f,
        leftBrow = 0f, rightBrow = 0f;

    UdpClient udpClient;
    Thread listenerThread;
    volatile bool running = false;

    void Start()
    {
        udpClient = new UdpClient(listenPort);
        running = true;
        listenerThread = new Thread(() => {
            IPEndPoint ep = new IPEndPoint(IPAddress.Any, 0);
            while (running)
            {
                try
                {
                    byte[] data = udpClient.Receive(ref ep);
                    string json = Encoding.UTF8.GetString(data);
                    FacePacket pkt = JsonUtility.FromJson<FacePacket>(json);
                    if (pkt.mouth != null) mouthOpen = pkt.mouth.open;
                    if (pkt.left_eye != null) leftEyeOpen = pkt.left_eye.open;
                    if (pkt.right_eye != null) rightEyeOpen = pkt.right_eye.open;
                    if (pkt.brow != null) { leftBrow = pkt.brow.left; rightBrow = pkt.brow.right;}
                }
                catch (Exception e)
                {
                    Debug.LogWarning("UDP error: " + e.Message);
                }
            }
        });
        listenerThread.IsBackground = true;
        listenerThread.Start();
    }

    void OnDestroy()
    {
        running = false;
        try { udpClient?.Close(); } catch { }
        if (listenerThread != null && listenerThread.IsAlive) listenerThread.Join(100);
    }

    void Update()
    {
        // DEBUG LOG
        Debug.Log($"mouth:{mouthOpen:F2}, leftEye:{leftEyeOpen:F2}, rightEye:{rightEyeOpen:F2}, leftBrow:{leftBrow:F2}, rightBrow:{rightBrow:F2}");

        // Mulut
        if (mouthMeshRenderer != null)
        {
            float val = Mathf.Clamp01(mouthOpen) * mouthOpenScale;
            mouthMeshRenderer.SetBlendShapeWeight(mouthOpenBlendIndex, val);
        }
        // Mata - independent blink
        if (eyeMeshRenderer != null)
        {
            float leftBlink = (1f - Mathf.Clamp01(leftEyeOpen)) * eyeBlinkScale;
            float rightBlink = (1f - Mathf.Clamp01(rightEyeOpen)) * eyeBlinkScale;
            eyeMeshRenderer.SetBlendShapeWeight(leftEyeBlinkBlendIndex, leftBlink);
            eyeMeshRenderer.SetBlendShapeWeight(rightEyeBlinkBlendIndex, rightBlink);
        }

        // Alis
        if (browMeshRenderer != null)
        {
            browMeshRenderer.SetBlendShapeWeight(leftBrowRaiseBlendIndex, Mathf.Clamp(leftBrow, -1f, 1f) * browRaiseScale);
            browMeshRenderer.SetBlendShapeWeight(rightBrowRaiseBlendIndex, Mathf.Clamp(rightBrow, -1f, 1f) * browRaiseScale);
        }
    }

    [Serializable] class MouthObj { public float open; }
    [Serializable] class EyeObj { public float open; }
    [Serializable] class BrowObj { public float left; public float right; }
    [Serializable] class FacePacket {
        public MouthObj mouth;
        public EyeObj left_eye;
        public EyeObj right_eye;
        public BrowObj brow;
    }
}