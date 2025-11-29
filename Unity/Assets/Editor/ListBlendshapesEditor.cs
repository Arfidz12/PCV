using UnityEngine;
using UnityEditor;
using System.Collections.Generic;

// Editor window: Tools -> Blendshape Inspector
public class ListBlendshapesEditor : EditorWindow
{
    Vector2 scroll;
    [MenuItem("Tools/Blendshape Inspector")]
    public static void ShowWindow()
    {
        EditorWindow.GetWindow(typeof(ListBlendshapesEditor), false, "Blendshape Inspector");
    }

    void OnGUI()
    {
        if (GUILayout.Button("Scan Scene Objects")) Repaint();
        if (GUILayout.Button("Scan Project Prefabs")) Repaint();

        scroll = GUILayout.BeginScrollView(scroll);

        GUILayout.Label("Scene SkinnedMeshRenderers", EditorStyles.boldLabel);
        var sceneSMRs = FindObjectsOfType<SkinnedMeshRenderer>();
        if (sceneSMRs.Length == 0)
            GUILayout.Label("No SkinnedMeshRenderer found in active scene.");
        else
        {
            foreach (var smr in sceneSMRs)
            {
                DrawSMRInfo(smr.gameObject.name + " (Scene)", smr);
            }
        }

        GUILayout.Space(10);
        GUILayout.Label("Project Prefab SkinnedMeshRenderers", EditorStyles.boldLabel);
        string[] guids = AssetDatabase.FindAssets("t:Prefab");
        foreach (string guid in guids)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null) continue;
            var smrs = prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            foreach (var smr in smrs)
            {
                DrawSMRInfo(prefab.name + " -> " + smr.gameObject.name + " (" + path + ")", smr);
            }
        }

        GUILayout.EndScrollView();
    }

    void DrawSMRInfo(string title, SkinnedMeshRenderer smr)
    {
        GUILayout.BeginVertical("box");
        GUILayout.Label(title, EditorStyles.label);
        Mesh mesh = smr.sharedMesh;
        if (mesh == null)
        {
            GUILayout.Label("  (no mesh)");
        }
        else
        {
            int bc = mesh.blendShapeCount;
            GUILayout.Label("  BlendShapeCount: " + bc);
            for (int i = 0; i < bc; i++)
            {
                string name = mesh.GetBlendShapeName(i);
                GUILayout.Label("    [" + i + "] " + name);
            }
        }
        if (GUILayout.Button("Ping in Project/Hierarchy"))
        {
            string assetPath = AssetDatabase.GetAssetPath(smr.gameObject);
            if (!string.IsNullOrEmpty(assetPath))
            {
                var obj = AssetDatabase.LoadAssetAtPath<Object>(assetPath);
                EditorGUIUtility.PingObject(obj);
            }
            else
            {
                EditorGUIUtility.PingObject(smr.gameObject);
            }
        }
        GUILayout.EndVertical();
    }
}